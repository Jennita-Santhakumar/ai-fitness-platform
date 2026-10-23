"""
Tests for Day 31: Plan-Quality Evaluation.
Tests prompt set validity, constraint evaluation engine, and run_evaluation execution.
"""
import json
import os
import pytest

from eval.run_eval import MockEvalProvider, evaluate_constraints, run_evaluation
from app.schemas.plan import Day, ExerciseItem, Plan, Week


class TestEvaluationSuite:
    """Verifies prompt bank and constraint evaluation engine."""

    def test_prompts_file_has_30_valid_entries(self):
        prompts_path = "eval/prompts.json"
        assert os.path.exists(prompts_path)
        with open(prompts_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert len(data) == 30
        for item in data:
            assert "id" in item
            assert "goal" in item
            assert "level" in item
            assert "equipment" in item
            assert "days_per_week" in item
            assert "weeks" in item
            assert 1 <= item["days_per_week"] <= 7
            assert 1 <= item["weeks"] <= 12

    def test_evaluate_constraints_detects_mismatches(self):
        # A plan with 2 weeks and 2 days/week
        plan = Plan(
            goal="Strength",
            level="Intermediate",
            weeks=[
                Week(
                    number=w,
                    days=[
                        Day(
                            name=f"Day {d}",
                            focus="Conditioning",
                            exercises=[
                                ExerciseItem(name="Barbell Deadlift", sets=3, reps=5, rest_sec=90)
                            ],
                        )
                        for d in range(1, 3)
                    ],
                )
                for w in range(1, 3)
            ],
        )

        # 1. Spec requesting 4 weeks -> should fail week count check
        spec1 = {"weeks": 4, "days_per_week": 2, "equipment": "Full Gym"}
        valid1, issues1 = evaluate_constraints(plan, spec1)
        assert valid1 is False
        assert any("Expected 4 weeks" in i for i in issues1)

        # 2. Spec requesting Bodyweight Only -> should fail equipment check due to Barbell
        spec2 = {"weeks": 2, "days_per_week": 2, "equipment": "Bodyweight Only"}
        valid2, issues2 = evaluate_constraints(plan, spec2)
        assert valid2 is False
        assert any("Equipment violation" in i for i in issues2)

        # 3. Spec requesting Full Gym with lower back pain -> should fail safety on conventional deadlift
        spec3 = {"weeks": 2, "days_per_week": 2, "equipment": "Full Gym", "injuries": "Lower back pain"}
        valid3, issues3 = evaluate_constraints(plan, spec3)
        assert valid3 is False
        assert any("Safety violation" in i for i in issues3)

        # 4. Perfectly matching spec
        good_plan = Plan(
            goal="Fitness",
            level="Beginner",
            weeks=[
                Week(
                    number=w,
                    days=[
                        Day(
                            name=f"Day {d}",
                            focus="Full Body",
                            exercises=[
                                ExerciseItem(name="Push-up", sets=3, reps=10, rest_sec=60)
                            ],
                        )
                        for d in range(1, 4)
                    ],
                )
                for w in range(1, 5)
            ],
        )
        spec_good = {"weeks": 4, "days_per_week": 3, "equipment": "Bodyweight Only", "injuries": "None"}
        valid_good, issues_good = evaluate_constraints(good_plan, spec_good)
        assert valid_good is True
        assert len(issues_good) == 0

    def test_run_evaluation_execution(self, tmp_path):
        out_report = str(tmp_path / "eval_out.md")
        metrics = run_evaluation(
            prompts_path="eval/prompts.json",
            mock_provider=True,
            output_md=out_report,
        )

        assert metrics["total"] == 30
        assert metrics["schema_pct"] == 100.0
        assert metrics["constraint_pct"] == 100.0
        assert os.path.exists(out_report)
