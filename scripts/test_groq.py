"""Throwaway test script for Groq provider verification."""
import os
import sys

# Ensure app package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.llm.groq_provider import GroqProvider


def main():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Notice: GROQ_API_KEY is not set in environment.")
        print("To test live: $env:GROQ_API_KEY='gsk_...'; python scripts/test_groq.py")
        return

    print("Connecting to Groq API with 20s timeout...")
    provider = GroqProvider(api_key=api_key)
    try:
        response = provider.generate(
            prompt="Say hello and return a JSON object with a 'greeting' key.",
            system_prompt="You are a helpful assistant. Output JSON only.",
        )
        print("\n--- Response Received ---")
        print(response)
    except Exception as e:
        print(f"Error during generation: {e}")


if __name__ == "__main__":
    main()
