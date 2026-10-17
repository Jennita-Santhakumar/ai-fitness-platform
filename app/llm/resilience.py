import json
import logging
from typing import Dict, Any, List, Optional, Tuple

from pydantic import ValidationError

from app.core.exceptions import PlanGenerationError
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.llm.prompts import (
    get_system_prompt,
    get_user_prompt,
    strip_code_fences,
)
from app.schemas.plan import Plan

logger = logging.getLogger("ai_fitness.llm.resilience")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


DEFAULT_PROVIDER_CHAIN = ["groq", "gemini", "ollama"]


def generate_plan_with_failover(
    inputs: Dict[str, Any],
    provider_chain: Optional[List[str]] = None,
    max_retries: int = 2,
    custom_providers: Optional[List[LLMProvider]] = None,
) -> Tuple[Plan, str, int]:
    """
    Executes multi-provider failover with self-correction retry loop.

    1. Attempts generation across providers in sequence: [Groq -> Gemini -> Ollama].
    2. If a provider returns invalid JSON or schema violations, retries up to `max_retries`
       times, appending the validation error back to the user prompt.
    3. If a provider times out or fails network requests, immediately falls over to next provider.
    4. Logs which provider answered and how many retries were needed.
    5. Raises PlanGenerationError if the entire chain is exhausted.

    Returns:
        Tuple[Plan, str, int]: (Validated Plan, Provider Name, Retries Used)
    """
    system_prompt = get_system_prompt()
    base_user_prompt = get_user_prompt(inputs)

    # Use custom provider instances (e.g. In tests) or resolve by string names
    providers: List[Tuple[str, LLMProvider]] = []
    if custom_providers:
        for p in custom_providers:
            providers.append((p.__class__.__name__, p))
    else:
        chain_names = provider_chain or DEFAULT_PROVIDER_CHAIN
        for name in chain_names:
            try:
                provider_instance = get_llm_provider(name)
                providers.append((name, provider_instance))
            except Exception as e:
                logger.warning(
                    f"Skipping provider initialization for '{name}': {str(e)}"
                )

    if not providers:
        raise PlanGenerationError("No LLM providers available in failover chain.")

    chain_errors = []

    for provider_name, provider in providers:
        current_user_prompt = base_user_prompt
        retries_used = 0

        while retries_used <= max_retries:
            try:
                logger.info(
                    f"Calling provider='{provider_name}' attempt={retries_used + 1}/{max_retries + 1}"
                )
                raw_response = provider.generate(
                    prompt=current_user_prompt, system_prompt=system_prompt
                )
                cleaned_json_str = strip_code_fences(raw_response)

                try:
                    plan_dict = json.loads(cleaned_json_str)
                except json.JSONDecodeError as json_err:
                    raise ValueError(f"Invalid JSON syntax: {str(json_err)}") from json_err

                validated_plan = Plan.model_validate(plan_dict)

                logger.info(
                    f"Plan generation successful: provider='{provider_name}' retries={retries_used}"
                )
                return validated_plan, provider_name, retries_used

            except (ValueError, ValidationError) as validation_err:
                retries_used += 1
                error_msg = str(validation_err)
                logger.warning(
                    f"Validation failed on provider='{provider_name}' "
                    f"retry={retries_used}/{max_retries}. Error: {error_msg}"
                )

                if retries_used <= max_retries:
                    # Append error feedback for self-correction prompt
                    current_user_prompt = (
                        f"{base_user_prompt}\n\n"
                        f"CRITICAL ERROR IN PREVIOUS ATTEMPT:\n"
                        f"{error_msg}\n\n"
                        f"Please correct the error, satisfy all constraints, and output valid JSON only."
                    )
                else:
                    chain_errors.append(
                        f"{provider_name} exceeded max retries: {error_msg}"
                    )
                    break

            except Exception as provider_err:
                # Network timeout, API error, or connection refusal -> Move to next provider immediately
                logger.warning(
                    f"Provider '{provider_name}' encountered an error: {str(provider_err)}. "
                    "Failing over to next provider..."
                )
                chain_errors.append(f"{provider_name} error: {str(provider_err)}")
                break

    # If all providers failed
    error_summary = " | ".join(chain_errors)
    logger.error(f"All providers exhausted. Summary: {error_summary}")
    raise PlanGenerationError(
        f"All LLM providers failed to generate a valid plan: {error_summary}",
        details={"errors": chain_errors},
    )
