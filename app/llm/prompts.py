import json
import logging
import re
from typing import Dict, Any, List, Optional

from app.schemas.plan import Plan
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider

try:
    from app.services.memory import query_memory
except ImportError:
    query_memory = None

logger = logging.getLogger("ai_fitness.prompts")


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


def get_user_prompt(inputs: Dict[str, Any], memory_context: Optional[str] = None) -> str:
    """
    Formats user fitness requirements into a structured prompt.
    Optionally includes memory context retrieved from ChromaDB.
    """
    goal = inputs.get("goal", "General Fitness")
    level = inputs.get("level", "Intermediate")
    equipment = inputs.get("equipment", "Full Gym")
    days_per_week = inputs.get("days_per_week", 3)
    duration_weeks = inputs.get("weeks", 4)
    injuries = inputs.get("injuries", "None")

    prompt = (
        f"Generate a customized workout plan with the following specifications:\n"
        f"- Primary Goal: {goal}\n"
        f"- Experience Level: {level}\n"
        f"- Available Equipment: {equipment}\n"
        f"- Days per Week: {days_per_week}\n"
        f"- Duration in Weeks: {duration_weeks}\n"
        f"- Physical Limitations / Injuries: {injuries}\n"
    )

    if memory_context:
        prompt += (
            f"\n--- TRAINING HISTORY CONTEXT ---\n"
            f"The following is the user's recent training history and past plans. "
            f"Use this context to personalise the plan — avoid repeating the same "
            f"exercises if the user has been doing them recently, and ensure progressive "
            f"overload based on their recent performance:\n\n"
            f"{memory_context}\n"
            f"--- END TRAINING HISTORY ---\n"
        )

    prompt += f"\nGenerate the full {duration_weeks}-week progression complying strictly with the JSON schema."
    return prompt


def retrieve_memory_context(user_id: int, inputs: Dict[str, Any], n_results: int = 5) -> Optional[str]:
    """
    Retrieves relevant training history from ChromaDB to inject as context
    into the plan generation prompt.

    Returns a formatted string of relevant memories, or None if the user
    has no memory store or no relevant results.
    """
    if query_memory is None:
        logger.debug("ChromaDB memory service not available, skipping memory retrieval")
        return None

    # Build a query from the user's plan inputs
    goal = inputs.get("goal", "workout")
    level = inputs.get("level", "")
    equipment = inputs.get("equipment", "")
    query_text = f"{goal} {level} {equipment}".strip()

    if not query_text:
        return None

    try:
        results = query_memory(user_id=user_id, query_text=query_text, n_results=n_results)
    except Exception as exc:
        logger.warning(f"Memory retrieval failed for user {user_id}: {exc}")
        return None

    if not results:
        return None

    # Format results into context string
    context_parts = []
    for i, item in enumerate(results, 1):
        doc = item.get("document", "")
        meta = item.get("metadata", {})
        doc_type = meta.get("type", "unknown")
        date_str = meta.get("date", "")
        header = f"[{doc_type.upper()}]"
        if date_str:
            header += f" ({date_str})"
        context_parts.append(f"{i}. {header}: {doc}")

    return "\n".join(context_parts)


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


def generate_plan(inputs: Dict[str, Any], provider: Optional[LLMProvider] = None, user_id: Optional[int] = None) -> Plan:
    """
    Generates a validated Plan from user inputs using the configured LLM provider.
    
    1. Optionally retrieves relevant memory context from ChromaDB (if user_id provided).
    2. Formats system & user prompts.
    3. Calls the LLM provider.
    4. Strips code fences and isolates JSON.
    5. Parses JSON and validates against the strict Plan Pydantic schema.
    """
    llm = provider or get_llm_provider()
    system_prompt = get_system_prompt()

    # Retrieve memory context if user_id is available
    memory_context = None
    if user_id is not None:
        memory_context = retrieve_memory_context(user_id=user_id, inputs=inputs)
        if memory_context:
            logger.info(f"Injected memory context for user_id={user_id} into plan prompt")

    user_prompt = get_user_prompt(inputs, memory_context=memory_context)

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
