from typing import Optional
import httpx
from app.core.config import settings
from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    """
    Google Gemini LLM Provider implementation.
    Communicates via Google Generative Language REST API with an enforced 20s timeout.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 20.0,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Send a completion request to Google Gemini with an enforced 20-second timeout.
        """
        if not self.api_key:
            raise ValueError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file."
            )

        url = f"{self.BASE_URL}/{self.model}:generateContent?key={self.api_key}"

        # Gemini payload structure
        contents = []
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [{"text": f"System Instruction: {system_prompt}"}]
            })
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                candidates = data.get("candidates", [])
                if not candidates:
                    raise RuntimeError("Gemini returned empty candidates in response.")
                
                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    raise RuntimeError("Gemini returned no text parts in candidate.")
                    
                return parts[0].get("text", "")
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Gemini API request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Gemini API returned HTTP error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Unexpected Gemini client failure: {str(exc)}") from exc
