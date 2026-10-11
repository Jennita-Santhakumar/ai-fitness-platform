from unittest.mock import patch, MagicMock
import httpx
import pytest
from app.llm.base import LLMProvider
from app.llm.groq_provider import GroqProvider


def test_groq_provider_subclasses_base():
    """Verify GroqProvider adheres to the LLMProvider abstract interface."""
    assert issubclass(GroqProvider, LLMProvider)


def test_groq_provider_missing_api_key_raises_value_error():
    """Verify GroqProvider raises ValueError when API key is missing."""
    provider = GroqProvider(api_key="")
    with pytest.raises(ValueError, match="Groq API key is not configured"):
        provider.generate(prompt="Hello")


@patch("httpx.Client.post")
def test_groq_provider_successful_generation(mock_post):
    """Verify GroqProvider successfully parses completion response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"greeting": "Hello, Athlete!"}'
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    provider = GroqProvider(api_key="mock_test_key")
    result = provider.generate(
        prompt="Say hello in JSON",
        system_prompt="You are a fitness coach. Return JSON.",
    )

    assert result == '{"greeting": "Hello, Athlete!"}'
    mock_post.assert_called_once()


@patch("httpx.Client.post")
def test_groq_provider_timeout_raises_timeout_error(mock_post):
    """Verify GroqProvider catches httpx.TimeoutException and raises TimeoutError."""
    mock_post.side_effect = httpx.TimeoutException("Read timed out")

    provider = GroqProvider(api_key="mock_test_key", timeout=20.0)
    with pytest.raises(TimeoutError, match="Groq API request timed out after 20.0 seconds"):
        provider.generate(prompt="Generate a workout plan")
