#!/usr/bin/env python3
"""
Plan-Quality Evaluation Suite (Day 31).
Runs a battery of 30 diverse user prompts against the LLM workout plan generator,
measuring schema validity, constraint adherence, latency, and provider reliability.
Outputs findings to docs/eval_results.md.
"""
import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.llm.base import LLMProvider
from app.llm.resilience import generate_plan_with_failover
from app.schemas.plan import Plan


class MockEvalProvider(LLMProvider):
    """Deterministic LLM Provider used for automated testing of the evaluation runner."""

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        # Extract requested weeks and days from prompt if present
        weeks = 4
        days = 3
        if "Duration in Weeks:" in prompt:
            try:
                line = [l for l in prompt.split("\n") if "Duration in Weeks:" in l][0]
                weeks = int(line.split(":")[1].strip())
            except Exception:
                pass
        if "Days per Week:" in prompt:
            try:
                line = [l for l in prompt.split("\n") if "Days per Week:" in l][0]
                days = int(line.split(":")[1].strip())
            except Exception:
                pass

        # Check equipment
        ex_name = "Push-up"
        if "Dumbbells" in prompt:
            ex_name = "Dumbbell Press"
        elif "Barbell" in prompt or "Full Gym" in prompt:
            ex_name = "Bench Press"

        plan = {
            "goal": "Fitness",
            "level": "Intermediate",
            "weeks": [
                {
                    "number": w,
                    "days": [
                        {
                            "name": f"Day {d}",
                            "focus": "Full Body Conditioning",
                            "exercises": [
                                {"name": ex_name, "sets": 3, "reps": 10, "rest_sec": 60, "notes": "Good form"}
                            ],
                        }
                        for d in range(1, days + 1)
                    ],
                }
                for w in range(1, weeks + 1)
            ],
        }
        return json.dumps(plan)


def evaluate_constraints(plan: Plan, prompt_spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates domain-level constraints beyond basic schema validity:
    1. Weeks count matches requested duration.
    2. Days per week matches requested frequency.
    3. Excluded equipment rules.
    4. Contraindicated exercise checks if injuries/limits specified.
    """
    issues = []
    req_weeks = prompt_spec.get("weeks", 4)
    req_days = prompt_spec.get("days_per_week", 3)
    equipment = prompt_spec.get("equipment", "")
    injuries = prompt_spec.get("injuries", "")

    # 1. Check week count
    if len(plan.weeks) != req_weeks:
        issues.append(f"Expected {req_weeks} weeks, got {len(plan.weeks)}")

    # 2. Check days count
    for week in plan.weeks:
        if len(week.days) != req_days:
            issues.append(f"Week {week.number}: Expected {req_days} days, got {len(week.days)}")
            break

    # 3. Check equipment adherence
    bodyweight_only = "Bodyweight" in equipment
    dumbbell_only = "Dumbbells" in equipment

    contraindicated_barbell = ["barbell", "bench press", "squat rack", "deadlift"]
    for week in plan.weeks:
        for day in week.days:
            for ex in day.exercises:
                name_lower = ex.name.lower()
                if bodyweight_only:
                    if any(c in name_lower for c in ["barbell", "dumbbell", "machine", "cable"]):
                        issues.append(f"Equipment violation: '{ex.name}' programmed for bodyweight-only plan")
                        break
                elif dumbbell_only:
                    if any(c in name_lower for c in ["barbell", "squat rack"]):
                        issues.append(f"Equipment violation: '{ex.name}' programmed for dumbbell-only plan")
                        break

    # 4. Injury contraindication checks
    if "lower back" in injuries.lower():
        for week in plan.weeks:
            for day in week.days:
                for ex in day.exercises:
                    if "deadlift" in ex.name.lower():
                        issues.append(f"Safety violation: '{ex.name}' contraindicated for lower back pain")
                        break

    return (len(issues) == 0, issues)


def run_evaluation(
    prompts_path: str = "eval/prompts.json",
    mock_provider: bool = False,
    output_md: str = "docs/eval_results.md",
) -> Dict[str, Any]:
    """Runs evaluation on all prompts and writes a Markdown report."""
    with open(prompts_path, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    providers = [MockEvalProvider()] if mock_provider else None

    results = []
    schema_valid_count = 0
    constraint_valid_count = 0
    latencies = []

    for item in prompts:
        p_id = item["id"]
        goal = item["goal"]
        req_inputs = {
            "goal": item["goal"],
            "level": item["level"],
            "equipment": item["equipment"],
            "days_per_week": item["days_per_week"],
            "weeks": item["weeks"],
            "injuries": item.get("injuries", "None"),
        }

        start_time = time.perf_counter()
        schema_valid = False
        constraint_valid = False
        retries_used = 0
        provider_name = "MockEval" if mock_provider else "Groq"
        issues = []

        try:
            plan, provider_name, retries_used = generate_plan_with_failover(
                inputs=req_inputs,
                custom_providers=providers,
            )
            schema_valid = True
            schema_valid_count += 1

            constraint_valid, issues = evaluate_constraints(plan, req_inputs)
            if constraint_valid:
                constraint_valid_count += 1
        except Exception as exc:
            issues.append(f"Generation failed: {str(exc)}")

        elapsed = round(time.perf_counter() - start_time, 2)
        latencies.append(elapsed)

        results.append({
            "id": p_id,
            "goal": goal,
            "level": req_inputs["level"],
            "equipment": req_inputs["equipment"],
            "schema_valid": schema_valid,
            "constraint_valid": constraint_valid,
            "retries": retries_used,
            "provider": provider_name,
            "latency": elapsed,
            "issues": issues,
        })

    total = len(prompts)
    schema_pct = round((schema_valid_count / total) * 100, 1)
    constraint_pct = round((constraint_valid_count / total) * 100, 1)
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    # Write Markdown summary table
    os.makedirs(os.path.dirname(output_md), exist_ok=True)
    with open(output_md, "w", encoding="utf-8") as out:
        out.write("# LLM Workout Plan Evaluation Results\n\n")
        out.write(f"Evaluated on {total} diverse persona prompts.\n\n")
        out.write("### 📊 Key Performance Metrics\n\n")
        out.write(f"- **Schema Validity Rate**: `{schema_pct}%` ({schema_valid_count}/{total})\n")
        out.write(f"- **Constraint Adherence Rate**: `{constraint_pct}%` ({constraint_valid_count}/{total})\n")
        out.write(f"- **Average Inference Latency**: `{avg_latency}s`\n\n")
        out.write("### Detailed Evaluation Breakdown\n\n")
        out.write("| # | Goal | Level | Equipment | Schema Valid | Constraint Match | Retries | Provider | Latency |\n")
        out.write("|---|------|-------|-----------|:------------:|:----------------:|:-------:|:--------:|:-------:|\n")
        for r in results:
            s_icon = "✅" if r["schema_valid"] else "❌"
            c_icon = "✅" if r["constraint_valid"] else "❌"
            out.write(
                f"| {r['id']} | {r['goal']} | {r['level']} | {r['equipment']} | {s_icon} | {c_icon} | {r['retries']} | {r['provider']} | {r['latency']}s |\n"
            )

    return {
        "total": total,
        "schema_valid_count": schema_valid_count,
        "schema_pct": schema_pct,
        "constraint_valid_count": constraint_valid_count,
        "constraint_pct": constraint_pct,
        "avg_latency": avg_latency,
        "results": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM workout plan evaluation.")
    parser.add_argument("--mock", action="store_true", help="Use deterministic mock provider")
    args = parser.parse_args()

    print(f"Running evaluation on 30 test prompts (mock={args.mock})...")
    metrics = run_evaluation(mock_provider=args.mock)
    print(f"Done! {metrics['schema_pct']}% valid plans, {metrics['constraint_pct']}% constraint adherence.")
    print("Report written to docs/eval_results.md")
