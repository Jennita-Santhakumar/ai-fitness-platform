import pytest
from pydantic import ValidationError
from app.schemas.plan import Plan, Week, Day, ExerciseItem


def sample_valid_plan_dict():
    return {
        "goal": "Hypertrophy",
        "level": "Intermediate",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Monday",
                        "focus": "Upper Body Strength",
                        "exercises": [
                            {
                                "name": "Barbell Bench Press",
                                "sets": 4,
                                "reps": 8,
                                "rest_sec": 90,
                                "notes": "RPE 8",
                            },
                            {
                                "name": "Overhead Press",
                                "sets": 3,
                                "reps": 10,
                                "rest_sec": 60,
                                "notes": None,
                            },
                        ],
                    },
                    {
                        "name": "Wednesday",
                        "focus": "Lower Body Power",
                        "exercises": [
                            {
                                "name": "Barbell Squat",
                                "sets": 4,
                                "reps": 6,
                                "rest_sec": 120,
                                "notes": "Full depth",
                            }
                        ],
                    },
                ],
            }
        ],
    }


def test_valid_plan_parses_successfully():
    """1. Test that a well-formed multi-week plan validates without error."""
    data = sample_valid_plan_dict()
    plan = Plan.model_validate(data)
    assert plan.goal == "Hypertrophy"
    assert len(plan.weeks) == 1
    assert len(plan.weeks[0].days) == 2
    assert plan.weeks[0].days[0].exercises[0].name == "Barbell Bench Press"


def test_invalid_weeks_count_rejected():
    """2. Test that weeks < 1 or > 12 raises ValidationError."""
    data = sample_valid_plan_dict()
    data["weeks"] = []  # 0 weeks
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "weeks" in str(exc_info.value).lower()

    # Create 13 weeks
    data["weeks"] = [
        {"number": i, "days": [{"name": "Mon", "focus": "Legs", "exercises": [{"name": "Squat", "sets": 3, "reps": 10, "rest_sec": 60}]}]}
        for i in range(1, 14)
    ]
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "weeks" in str(exc_info.value).lower()


def test_invalid_days_per_week_rejected():
    """3. Test that days per week < 1 or > 7 raises ValidationError."""
    data = sample_valid_plan_dict()
    data["weeks"][0]["days"] = []  # 0 days in a week
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "days" in str(exc_info.value).lower()

    # 8 days in a week
    data["weeks"][0]["days"] = [
        {"name": f"Day {i}", "focus": "Cardio", "exercises": [{"name": "Run", "sets": 1, "reps": 1, "rest_sec": 0}]}
        for i in range(1, 9)
    ]
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "days" in str(exc_info.value).lower()


def test_invalid_sets_or_reps_rejected():
    """4. Test that sets <= 0 or reps <= 0 raises ValidationError."""
    data = sample_valid_plan_dict()
    data["weeks"][0]["days"][0].get("exercises")[0]["sets"] = 0
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "sets" in str(exc_info.value).lower()

    data = sample_valid_plan_dict()
    data["weeks"][0]["days"][0].get("exercises")[0]["reps"] = -5
    with pytest.raises(ValidationError) as exc_info:
        Plan.model_validate(data)
    assert "reps" in str(exc_info.value).lower()


def test_model_json_schema_export():
    """5. Test that Plan.model_json_schema() produces valid JSON schema with definitions."""
    schema = Plan.model_json_schema()
    assert schema["type"] == "object"
    assert "goal" in schema["properties"]
    assert "level" in schema["properties"]
    assert "weeks" in schema["properties"]
    assert "$defs" in schema
    assert "Week" in schema["$defs"]
    assert "Day" in schema["$defs"]
    assert "ExerciseItem" in schema["$defs"]
