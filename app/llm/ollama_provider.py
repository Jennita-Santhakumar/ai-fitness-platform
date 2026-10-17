from typing import Optional
import httpx
from app.core.config import settings
from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """
    Local Ollama LLM Provider implementation for offline, zero-cost inference.
    Communicates via Ollama's local REST API (http://localhost:11434).
    """

    DEFAULT_MODEL = "llama3.2"

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a completion request to local Ollama instance.
        """
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",  # Force Ollama to constrain generation to valid JSON
            "options": {
                "temperature": 0.2,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("response", "")
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Cannot connect to local Ollama at {self.base_url}. "
                "Ensure Ollama is installed and running (`ollama serve`)."
            ) from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama local generation timed out after {self.timeout} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Ollama returned HTTP error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected Ollama client failure: {str(exc)}") from exc
