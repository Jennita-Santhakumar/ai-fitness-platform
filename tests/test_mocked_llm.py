import json
from typing import List, Union, Optional
import pytest

from app.api.deps import get_llm_providers
from app.core.exceptions import PlanGenerationError
from app.llm.base import LLMProvider
from app.llm.resilience import generate_plan_with_failover
from app.main import app
from app.schemas.plan import Plan


class FakeProvider(LLMProvider):
    """
    Test double implementing LLMProvider.
    Yields pre-configured responses or raises exceptions in sequence.
    """

    def __init__(self, responses: Optional[List[Union[str, Exception]]] = None):
        self.responses = responses or []
        self.call_count = 0
        self.prompts_received = []

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        self.prompts_received.append((prompt, system_prompt))
        if self.call_count >= len(self.responses):
            raise RuntimeError(f"FakeProvider ran out of canned responses (called {self.call_count + 1} times).")

        item = self.responses[self.call_count]
        self.call_count += 1

        if isinstance(item, Exception):
            raise item
        return item


def sample_canned_plan_json(goal: str = "Cardio Health") -> str:
    return json.dumps({
        "goal": goal,
        "level": "Beginner",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Aerobic",
                        "exercises": [{"name": "Brisk Walking", "sets": 1, "reps": 1, "rest_sec": 0, "notes": "30 mins"}],
                    }
                ],
            }
        ],
    })


# --- Day 14 Unit Tests: Isolated FakeProvider Scenarios ---

def test_fake_provider_valid_json():
    """1. Test FakeProvider returning clean, valid JSON on first attempt."""
    fake = FakeProvider(responses=[sample_canned_plan_json("Endurance")])
    plan, provider_name, retries = generate_plan_with_failover(
        inputs={"goal": "Endurance"},
        custom_providers=[fake],
    )
    assert isinstance(plan, Plan)
    assert plan.goal == "Endurance"
    assert retries == 0
    assert fake.call_count == 1


def test_fake_provider_invalid_json_then_valid_on_retry():
    """2. Test FakeProvider returning malformed JSON on first attempt, then valid on retry."""
    fake = FakeProvider(responses=[
        "This is not JSON at all!",  # Attempt 1: Syntax error
        sample_canned_plan_json("Hypertrophy"),  # Attempt 2: Self-corrected valid JSON
    ])
    plan, provider_name, retries = generate_plan_with_failover(
        inputs={"goal": "Hypertrophy"},
        custom_providers=[fake],
        max_retries=2,
    )
    assert isinstance(plan, Plan)
    assert plan.goal == "Hypertrophy"
    assert retries == 1
    assert fake.call_count == 2
    # Check that error feedback was included in second prompt
    second_prompt = fake.prompts_received[1][0]
    assert "CRITICAL ERROR IN PREVIOUS ATTEMPT" in second_prompt


def test_fake_provider_always_invalid_raises_error():
    """3. Test FakeProvider returning persistent invalid responses exhausts retries and raises PlanGenerationError."""
    fake = FakeProvider(responses=[
        "Broken 1",
        "Broken 2",
        "Broken 3",
    ])
    with pytest.raises(PlanGenerationError) as exc_info:
        generate_plan_with_failover(
            inputs={"goal": "Strength"},
            custom_providers=[fake],
            max_retries=2,
        )
    assert "All LLM providers failed" in str(exc_info.value)
    assert fake.call_count == 3


def test_fake_provider_timeout_then_failover():
    """4. Test FakeProvider 1 timing out immediately fails over to FakeProvider 2."""
    fake1 = FakeProvider(responses=[TimeoutError("FakeProvider 1 connection timed out after 20s")])
    fake2 = FakeProvider(responses=[sample_canned_plan_json("Agility")])

    plan, provider_name, retries = generate_plan_with_failover(
        inputs={"goal": "Agility"},
        custom_providers=[fake1, fake2],
    )
    assert isinstance(plan, Plan)
    assert plan.goal == "Agility"
    assert retries == 0
    assert fake1.call_count == 1
    assert fake2.call_count == 1


# --- Day 14 Integration Test: Endpoint with Injected FakeProvider via dependency_overrides ---

def test_plans_generate_endpoint_with_injected_fake_provider(client, auth_headers):
    """5. Test POST /plans/generate with FakeProvider injected through FastAPI dependency_overrides."""
    fake_llm = FakeProvider(responses=[sample_canned_plan_json("Olympic Lifting")])
    app.dependency_overrides[get_llm_providers] = lambda: [fake_llm]

    headers = auth_headers("faketester@example.com")
    resp = client.post(
        "/plans/generate",
        json={"goal": "Olympic Lifting", "level": "Advanced", "weeks": 4},
        headers=headers,
    )

    app.dependency_overrides.pop(get_llm_providers, None)

    assert resp.status_code == 201
    data = resp.json()
    assert data["provider"] == "FakeProvider"
    assert data["plan"]["goal"] == "Olympic Lifting"
    assert fake_llm.call_count == 1
