from typing import Optional
import httpx
from app.core.config import settings
from app.llm.base import LLMProvider


class GroqProvider(LLMProvider):
    """
    Groq LLM Provider implementation using high-speed Llama 3 inference.
    Communicates via Groq's OpenAI-compatible REST API with an enforced 20s timeout.
    """

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 20.0,
    ):
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a completion request to Groq with an enforced 20-second timeout.
        """
        if not self.api_key:
            raise ValueError(
                "Groq API key is not configured. Please set GROQ_API_KEY in your .env file."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,  # Low temperature for deterministic, structured responses
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(self.API_URL, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Groq API request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Groq API returned HTTP error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected Groq client failure: {str(exc)}") from exc
