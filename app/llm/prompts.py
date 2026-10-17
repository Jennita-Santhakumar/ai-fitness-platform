import json
import re
from typing import Dict, Any, Optional

from app.schemas.plan import Plan
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider


def get_system_prompt() -> str:
    """
    Constructs the system prompt embedding the official Plan JSON Schema.
    """
    json_schema = json.dumps(Plan.model_json_schema(), indent=2)
    return (
        "You are an elite, certified strength and conditioning coach and exercise physiologist.\n"
        "Your task is to design a structured, progressive, multi-week workout plan tailored to the user's inputs.\n\n"
        "STRICT CONSTRAINTS:\n"
        "1. Output valid JSON ONLY. Never prepend conversational filler (e.g. 'Here is your plan:') or append sign-offs.\n"
        "2. Do NOT wrap output in markdown code fences unless unavoidable; raw JSON is preferred.\n"
        "3. You MUST conform exactly to the following JSON Schema:\n"
        f"{json_schema}\n\n"
        "SAFETY & PROGRAMMING RULES:\n"
        "- If injuries or physical limitations are specified, replace contraindicated exercises with joint-friendly alternatives.\n"
        "- Ensure balanced muscle group programming and appropriate progressive overload across weeks.\n"
        "- Sets and reps must strictly be positive integers (> 0).\n"
        "- Number of weeks must be between 1 and 12.\n"
        "- Number of days per week must be between 1 and 7.\n"
    )


def get_user_prompt(inputs: Dict[str, Any]) -> str:
    """
    Formats user fitness requirements into a structured prompt.
    """
    goal = inputs.get("goal", "General Fitness")
    level = inputs.get("level", "Intermediate")
    equipment = inputs.get("equipment", "Full Gym")
    days_per_week = inputs.get("days_per_week", 3)
    duration_weeks = inputs.get("weeks", 4)
    injuries = inputs.get("injuries", "None")

    return (
        f"Generate a customized workout plan with the following specifications:\n"
        f"- Primary Goal: {goal}\n"
        f"- Experience Level: {level}\n"
        f"- Available Equipment: {equipment}\n"
        f"- Days per Week: {days_per_week}\n"
        f"- Duration in Weeks: {duration_weeks}\n"
        f"- Physical Limitations / Injuries: {injuries}\n\n"
        f"Generate the full {duration_weeks}-week progression complying strictly with the JSON schema."
    )


def strip_code_fences(raw_text: str) -> str:
    """
    Removes markdown code fences (```json ... ``` or ``` ... ```)
    and strips leading/trailing non-JSON conversational text.
    """
    text = raw_text.strip()

    # Pattern matches ```json ... ``` or ``` ... ```
    fence_pattern = r"^```(?:json)?\s*([\s\S]*?)\s*```$"
    match = re.match(fence_pattern, text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()

    # In case there is lingering text before the first '{' or after the last '}'
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace : last_brace + 1]

    return text


def generate_plan(inputs: Dict[str, Any], provider: Optional[LLMProvider] = None) -> Plan:
    """
    Generates a validated Plan from user inputs using the configured LLM provider.
    
    1. Formats system & user prompts.
    2. Calls the LLM provider.
    3. Strips code fences and isolates JSON.
    4. Parses JSON and validates against the strict Plan Pydantic schema.
    """
    llm = provider or get_llm_provider()
    system_prompt = get_system_prompt()
    user_prompt = get_user_prompt(inputs)

    raw_response = llm.generate(prompt=user_prompt, system_prompt=system_prompt)
    cleaned_json_str = strip_code_fences(raw_response)

    try:
        plan_dict = json.loads(cleaned_json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned invalid JSON: {str(exc)}\nRaw output: {raw_response[:200]}"
        ) from exc

    # Pydantic validation
    return Plan.model_validate(plan_dict)
