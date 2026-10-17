from typing import Optional
from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.groq_provider import GroqProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.ollama_provider import OllamaProvider


def get_llm_provider(name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to retrieve an instantiated LLM provider.
    
    Args:
        name: Name of the provider ('groq', 'gemini', 'ollama').
              Defaults to settings.DEFAULT_LLM_PROVIDER.
              
    Returns:
        An instance conforming to LLMProvider.
        
    Raises:
        ValueError: If the requested provider name is not recognized.
    """
    provider_name = (name or settings.DEFAULT_LLM_PROVIDER).strip().lower()

    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
    else:
        raise ValueError(
            f"Unsupported LLM provider: '{name}'. "
            "Supported providers are: 'groq', 'gemini', 'ollama'."
        )
