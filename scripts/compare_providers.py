"""Compare response latency and outputs across configured LLM providers."""
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.llm.factory import get_llm_provider


def compare_providers():
    prompt = "Create a 1-day sample workout for a beginner with pushups and squats. Return JSON only with keys: name, exercises."
    system_prompt = "You are an elite fitness trainer. Output valid JSON only."

    providers = ["groq", "gemini", "ollama"]
    print(f"Benchmarking prompt across providers: {providers}\n")

    for name in providers:
        print(f"--- Testing Provider: {name.upper()} ---")
        try:
            provider = get_llm_provider(name)
            start_time = time.perf_counter()
            response = provider.generate(prompt=prompt, system_prompt=system_prompt)
            duration = time.perf_counter() - start_time
            print(f"Success! Latency: {duration:.2f}s")
            print(f"Response preview: {response[:150]}...\n")
        except Exception as e:
            print(f"Skipped / Failed ({name}): {e}\n")


if __name__ == "__main__":
    compare_providers()
