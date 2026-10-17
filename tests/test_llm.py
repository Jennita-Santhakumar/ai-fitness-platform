from unittest.mock import patch, MagicMock
import httpx
import pytest
from app.llm.base import LLMProvider
from app.llm.groq_provider import GroqProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.ollama_provider import OllamaProvider
from app.llm.factory import get_llm_provider


# --- Groq Provider Tests ---

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


# --- Gemini Provider Tests ---

def test_gemini_provider_subclasses_base():
    """Verify GeminiProvider adheres to the LLMProvider abstract interface."""
    assert issubclass(GeminiProvider, LLMProvider)


def test_gemini_provider_missing_api_key_raises_value_error():
    """Verify GeminiProvider raises ValueError when API key is missing."""
    provider = GeminiProvider(api_key="")
    with pytest.raises(ValueError, match="Gemini API key is not configured"):
        provider.generate(prompt="Hello")


@patch("httpx.Client.post")
def test_gemini_provider_successful_generation(mock_post):
    """Verify GeminiProvider successfully parses candidate parts response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '{"greeting": "Hello from Gemini!"}'}]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    provider = GeminiProvider(api_key="mock_gemini_key")
    result = provider.generate(
        prompt="Say hello in JSON",
        system_prompt="You are a fitness coach.",
    )

    assert result == '{"greeting": "Hello from Gemini!"}'
    mock_post.assert_called_once()


@patch("httpx.Client.post")
def test_gemini_provider_timeout_raises_timeout_error(mock_post):
    """Verify GeminiProvider catches httpx.TimeoutException and raises TimeoutError."""
    mock_post.side_effect = httpx.TimeoutException("Read timed out")

    provider = GeminiProvider(api_key="mock_gemini_key", timeout=20.0)
    with pytest.raises(TimeoutError, match="Gemini API request timed out after 20.0 seconds"):
        provider.generate(prompt="Generate plan")


# --- Ollama Provider Tests ---

def test_ollama_provider_subclasses_base():
    """Verify OllamaProvider adheres to the LLMProvider abstract interface."""
    assert issubclass(OllamaProvider, LLMProvider)


@patch("httpx.Client.post")
def test_ollama_provider_successful_generation(mock_post):
    """Verify OllamaProvider successfully parses JSON response from local daemon."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": '{"greeting": "Hello from Ollama!"}'
    }
    mock_post.return_value = mock_response

    provider = OllamaProvider(base_url="http://localhost:11434")
    result = provider.generate(
        prompt="Say hello in JSON",
        system_prompt="You are a local coach.",
    )

    assert result == '{"greeting": "Hello from Ollama!"}'
    mock_post.assert_called_once()


@patch("httpx.Client.post")
def test_ollama_provider_connection_failure(mock_post):
    """Verify OllamaProvider handles connection error when daemon is not running."""
    mock_post.side_effect = httpx.ConnectError("Failed to connect")

    provider = OllamaProvider(base_url="http://localhost:11434")
    with pytest.raises(RuntimeError, match="Cannot connect to local Ollama"):
        provider.generate(prompt="Generate plan")


# --- Provider Factory Tests ---

def test_get_llm_provider_factory():
    """Verify factory returns appropriate provider instance based on name."""
    groq = get_llm_provider("groq")
    assert isinstance(groq, GroqProvider)

    gemini = get_llm_provider("gemini")
    assert isinstance(gemini, GeminiProvider)

    ollama = get_llm_provider("ollama")
    assert isinstance(ollama, OllamaProvider)


def test_get_llm_provider_unsupported_raises_value_error():
    """Verify factory raises ValueError for invalid provider name."""
    with pytest.raises(ValueError, match="Unsupported LLM provider: 'anthropic'"):
        get_llm_provider("anthropic")
