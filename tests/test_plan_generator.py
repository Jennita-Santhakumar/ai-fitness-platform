import json
from unittest.mock import MagicMock
import pytest
from pydantic import ValidationError

from app.llm.base import LLMProvider
from app.llm.prompts import (
    strip_code_fences,
    get_system_prompt,
    get_user_prompt,
    generate_plan,
)
from app.schemas.plan import Plan


def sample_valid_plan_json_str():
    return json.dumps({
        "goal": "Strength Training",
        "level": "Intermediate",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Full Body Strength",
                        "exercises": [
                            {
                                "name": "Deadlift",
                                "sets": 3,
                                "reps": 5,
                                "rest_sec": 180,
                                "notes": "Reset each rep",
                            }
                        ],
                    }
                ],
            }
        ],
    })


def test_strip_code_fences_clean_markdown():
    """Verify code fences (```json ... ```) are cleanly stripped."""
    raw = "```json\n{\"goal\": \"Hypertrophy\"}\n```"
    assert strip_code_fences(raw) == '{"goal": "Hypertrophy"}'


def test_strip_code_fences_with_surrounding_conversational_text():
    """Verify leading and trailing commentary is removed."""
    raw = "Here is your customized workout plan:\n```json\n{\"goal\": \"Fat Loss\"}\n```\nHope you like it!"
    assert strip_code_fences(raw) == '{"goal": "Fat Loss"}'


def test_system_prompt_contains_json_schema():
    """Verify system prompt embeds the Pydantic Plan JSON schema."""
    sys_prompt = get_system_prompt()
    assert "Plan" in sys_prompt
    assert "ExerciseItem" in sys_prompt
    assert "STRICT CONSTRAINTS" in sys_prompt


def test_user_prompt_formats_variables():
    """Verify user prompt correctly interpolates parameters."""
    inputs = {
        "goal": "Marathon Prep",
        "level": "Advanced",
        "equipment": "Treadmill & Dumbbells",
        "days_per_week": 4,
        "weeks": 8,
        "injuries": "Shin splints",
    }
    user_prompt = get_user_prompt(inputs)
    assert "Marathon Prep" in user_prompt
    assert "Shin splints" in user_prompt
    assert "8-week" in user_prompt


def test_generate_plan_success():
    """Verify generate_plan successfully produces a validated Plan instance."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.generate.return_value = f"```json\n{sample_valid_plan_json_str()}\n```"

    inputs = {"goal": "Strength Training", "level": "Intermediate", "weeks": 1}
    plan = generate_plan(inputs=inputs, provider=mock_provider)

    assert isinstance(plan, Plan)
    assert plan.goal == "Strength Training"
    assert len(plan.weeks) == 1
    assert plan.weeks[0].days[0].exercises[0].name == "Deadlift"
    mock_provider.generate.assert_called_once()


def test_generate_plan_invalid_json_raises_value_error():
    """Verify invalid JSON from LLM raises ValueError."""
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.generate.return_value = "Sorry, I cannot generate a plan right now."

    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        generate_plan(inputs={}, provider=mock_provider)


def test_generate_plan_invalid_schema_raises_validation_error():
    """Verify bad structure (e.g. negative reps) raises ValidationError."""
    bad_data = {
        "goal": "Bad Plan",
        "level": "Beginner",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Legs",
                        "exercises": [{"name": "Squat", "sets": -1, "reps": -5}],  # Invalid
                    }
                ],
            }
        ],
    }
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.generate.return_value = json.dumps(bad_data)

    with pytest.raises(ValidationError):
        generate_plan(inputs={}, provider=mock_provider)
