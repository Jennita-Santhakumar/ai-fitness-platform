"""
Tests for Day 23: Memory retrieval in prompts.
Verifies that ChromaDB memory context is injected into plan generation prompts.
"""
import shutil
import tempfile
from unittest.mock import patch

import pytest

from app.llm.prompts import get_user_prompt, retrieve_memory_context
from app.services.memory import add_memory, reset_chroma_client


@pytest.fixture(autouse=True)
def chroma_temp_dir(monkeypatch):
    """Use a fresh temp directory for ChromaDB in each test."""
    tmpdir = tempfile.mkdtemp(prefix="chroma_prompt_test_")
    monkeypatch.setattr("app.services.memory._chroma_client", None)
    monkeypatch.setattr("app.core.config.settings.CHROMA_PERSIST_DIR", tmpdir)
    yield tmpdir
    reset_chroma_client()
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# get_user_prompt tests
# ---------------------------------------------------------------------------

class TestGetUserPrompt:
    def test_basic_prompt_without_memory(self):
        inputs = {"goal": "Strength", "level": "Beginner"}
        prompt = get_user_prompt(inputs)
        assert "Strength" in prompt
        assert "Beginner" in prompt
        assert "TRAINING HISTORY" not in prompt

    def test_prompt_with_memory_context(self):
        inputs = {"goal": "Hypertrophy", "level": "Advanced"}
        memory = "1. [SESSION] (2026-10-18): Heavy squats 5x5 at 140kg"
        prompt = get_user_prompt(inputs, memory_context=memory)
        assert "TRAINING HISTORY CONTEXT" in prompt
        assert "Heavy squats" in prompt
        assert "progressive overload" in prompt

    def test_prompt_preserves_all_inputs(self):
        inputs = {
            "goal": "Fat Loss",
            "level": "Intermediate",
            "equipment": "Dumbbells only",
            "days_per_week": 4,
            "weeks": 6,
            "injuries": "Lower back pain",
        }
        prompt = get_user_prompt(inputs)
        assert "Fat Loss" in prompt
        assert "Dumbbells only" in prompt
        assert "4" in prompt
        assert "6" in prompt
        assert "Lower back pain" in prompt


# ---------------------------------------------------------------------------
# retrieve_memory_context tests
# ---------------------------------------------------------------------------

class TestRetrieveMemoryContext:
    def test_returns_none_for_empty_store(self):
        result = retrieve_memory_context(user_id=999, inputs={"goal": "Strength"})
        assert result is None

    def test_retrieves_relevant_context(self):
        add_memory(
            user_id=42,
            doc_id="session_100",
            text="Heavy deadlifts 5x3 at 180kg with good form",
            metadata={"type": "session", "date": "2026-10-18"},
        )
        add_memory(
            user_id=42,
            doc_id="plan_10",
            text="4-week strength block focusing on compound lifts",
            metadata={"type": "plan"},
        )

        result = retrieve_memory_context(user_id=42, inputs={"goal": "Strength", "level": "Advanced"})
        assert result is not None
        assert "deadlifts" in result or "strength" in result.lower()

    def test_formats_results_with_headers(self):
        add_memory(
            user_id=42,
            doc_id="s1",
            text="Morning run 10km",
            metadata={"type": "session", "date": "2026-10-15"},
        )

        result = retrieve_memory_context(user_id=42, inputs={"goal": "Cardio"})
        assert result is not None
        assert "[SESSION]" in result
        assert "2026-10-15" in result

    def test_returns_none_on_import_error(self):
        with patch("app.llm.prompts.query_memory", None):
            result = retrieve_memory_context(user_id=42, inputs={"goal": "Cardio"})
            assert result is None

    def test_returns_none_on_query_failure(self):
        with patch("app.services.memory.get_or_create_user_collection", side_effect=Exception("DB error")):
            result = retrieve_memory_context(user_id=42, inputs={"goal": "Strength"})
            assert result is None

    def test_respects_n_results(self):
        for i in range(10):
            add_memory(
                user_id=42,
                doc_id=f"s{i}",
                text=f"Session {i} with exercises",
                metadata={"type": "session", "date": f"2026-10-{10+i}"},
            )

        result = retrieve_memory_context(user_id=42, inputs={"goal": "Fitness"}, n_results=3)
        assert result is not None
        # Should have exactly 3 numbered entries
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) == 3


# ---------------------------------------------------------------------------
# Integration: memory context in generate_plan
# ---------------------------------------------------------------------------

class TestGeneratePlanWithMemory:
    """Verify that generate_plan passes memory context to the prompt."""

    def test_plan_generation_uses_memory_context(self):
        # Seed some memories
        add_memory(
            user_id=42,
            doc_id="s_test",
            text="Did 3x10 bench press at 80kg",
            metadata={"type": "session", "date": "2026-10-20"},
        )

        inputs = {"goal": "Strength", "level": "Intermediate", "weeks": 4, "days_per_week": 3}

        # Mock the LLM to capture the prompt it receives
        captured_prompts = {}

        def mock_generate(prompt, system_prompt):
            captured_prompts["user_prompt"] = prompt
            # Return a minimal valid plan JSON
            import json
            plan = {
                "goal": "Strength",
                "level": "Intermediate",
                "weeks": [
                    {
                        "number": w,
                        "days": [
                            {
                                "name": "Day 1",
                                "focus": "Strength",
                                "exercises": [
                                    {"name": "Squat", "sets": 3, "reps": 10, "rest_sec": 90}
                                ],
                            }
                        ],
                    }
                    for w in range(1, 5)
                ],
            }
            return json.dumps(plan)

        from app.llm.base import LLMProvider

        class MockLLM(LLMProvider):
            def generate(self, prompt, system_prompt=None):
                return mock_generate(prompt, system_prompt)

        from app.llm.prompts import generate_plan

        plan = generate_plan(inputs=inputs, provider=MockLLM(), user_id=42)
        assert plan is not None
        # The prompt should contain the memory context
        assert "TRAINING HISTORY" in captured_prompts["user_prompt"]
        assert "bench press" in captured_prompts["user_prompt"]
