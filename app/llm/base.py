from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """
    Abstract Base Class for all LLM providers (Groq, Gemini, Ollama).
    Enforces a unified contract for text/JSON generation.
    """

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a completion for the given prompt.
        
        Args:
            prompt: The user prompt or instruction.
            system_prompt: Optional system persona or constraints.
            
        Returns:
            The raw text string response from the LLM.
            
        Raises:
            Exception: If provider times out, returns HTTP error, or fails.
        """
        pass
