import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import PlanGenerationError
from app.llm.base import LLMProvider
from app.llm.resilience import generate_plan_with_failover
from app.main import app
from app.schemas.plan import Plan


def sample_valid_plan_json():
    return json.dumps({
        "goal": "Endurance",
        "level": "Beginner",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Aerobic Base",
                        "exercises": [{"name": "Jogging", "sets": 1, "reps": 1, "rest_sec": 0}],
                    }
                ],
            }
        ],
    })


def test_retry_on_validation_error_succeeds_on_second_attempt():
    """Verify that a provider with a transient validation error self-corrects on retry."""
    provider = MagicMock(spec=LLMProvider)
    # First attempt: invalid JSON; Second attempt: valid plan JSON
    provider.generate.side_effect = [
        "Not JSON at all",
        sample_valid_plan_json(),
    ]

    plan, provider_name, retries = generate_plan_with_failover(
        inputs={"goal": "Endurance"},
        custom_providers=[provider],
        max_retries=2,
    )

    assert isinstance(plan, Plan)
    assert plan.goal == "Endurance"
    assert retries == 1
    assert provider.generate.call_count == 2


def test_failover_when_first_provider_times_out():
    """Verify failover to the next provider when the first provider raises TimeoutError."""
    failing_provider = MagicMock(spec=LLMProvider)
    failing_provider.generate.side_effect = TimeoutError("Groq timed out after 20.0s")

    working_provider = MagicMock(spec=LLMProvider)
    working_provider.generate.return_value = sample_valid_plan_json()

    plan, provider_name, retries = generate_plan_with_failover(
        inputs={"goal": "Endurance"},
        custom_providers=[failing_provider, working_provider],
        max_retries=2,
    )

    assert isinstance(plan, Plan)
    assert retries == 0
    failing_provider.generate.assert_called_once()
    working_provider.generate.assert_called_once()


def test_exhausted_chain_raises_plan_generation_error():
    """Verify PlanGenerationError is raised when every provider in the chain fails."""
    provider1 = MagicMock(spec=LLMProvider)
    provider1.generate.side_effect = TimeoutError("Timed out")

    provider2 = MagicMock(spec=LLMProvider)
    provider2.generate.side_effect = RuntimeError("Service Unavailable")

    with pytest.raises(PlanGenerationError) as exc_info:
        generate_plan_with_failover(
            inputs={"goal": "Endurance"},
            custom_providers=[provider1, provider2],
            max_retries=1,
        )

    assert "All LLM providers failed" in str(exc_info.value)


def test_plan_generation_error_maps_to_502_bad_gateway():
    """Verify FastAPI exception handler catches PlanGenerationError and returns HTTP 502."""
    client = TestClient(app)

    # Temporary endpoint to test exception handler
    @app.get("/test-502-failover")
    def trigger_error():
        raise PlanGenerationError("Upstream AI model failed", details={"errors": ["timeout"]})

    response = client.get("/test-502-failover")
    assert response.status_code == 502
    data = response.json()
    assert "Upstream AI model failed" in data["detail"]
    assert "timeout" in data["errors"]
