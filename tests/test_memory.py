"""
Tests for Day 22: ChromaDB Memory Store.
Uses a temp directory for ChromaDB persistence — no side effects on disk.
"""
import os
import shutil
import tempfile

import pytest

from app.services.memory import (
    add_memories_batch,
    add_memory,
    delete_memory,
    delete_user_collection,
    get_or_create_user_collection,
    ingest_plan_memory,
    ingest_session_memory,
    query_memory,
    reset_chroma_client,
)


@pytest.fixture(autouse=True)
def chroma_temp_dir(monkeypatch):
    """Use a fresh temp directory for ChromaDB in each test."""
    tmpdir = tempfile.mkdtemp(prefix="chroma_test_")
    monkeypatch.setattr("app.services.memory._chroma_client", None)
    monkeypatch.setattr("app.core.config.settings.CHROMA_PERSIST_DIR", tmpdir)
    yield tmpdir
    reset_chroma_client()
    shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Collection management
# ---------------------------------------------------------------------------

class TestCollectionManagement:
    def test_creates_user_collection(self):
        col = get_or_create_user_collection(user_id=1)
        assert col is not None
        assert "user_memory_1" in col.name

    def test_separate_collections_per_user(self):
        col1 = get_or_create_user_collection(user_id=1)
        col2 = get_or_create_user_collection(user_id=2)
        assert col1.name != col2.name


# ---------------------------------------------------------------------------
# Single document CRUD
# ---------------------------------------------------------------------------

class TestAddAndQueryMemory:
    def test_add_and_query_returns_result(self):
        add_memory(user_id=10, doc_id="doc_1", text="Upper body strength workout with bench press and rows")
        results = query_memory(user_id=10, query_text="chest exercises")
        assert len(results) >= 1
        assert results[0]["id"] == "doc_1"
        assert "bench press" in results[0]["document"]

    def test_upsert_overwrites_same_id(self):
        add_memory(user_id=10, doc_id="doc_up", text="Old workout")
        add_memory(user_id=10, doc_id="doc_up", text="Updated workout with squats")
        results = query_memory(user_id=10, query_text="squats")
        assert len(results) == 1
        assert "squats" in results[0]["document"]

    def test_query_empty_collection_returns_empty(self):
        results = query_memory(user_id=999, query_text="anything")
        assert results == []

    def test_query_with_metadata_filter(self):
        add_memory(user_id=10, doc_id="s1", text="Running session", metadata={"type": "session"})
        add_memory(user_id=10, doc_id="p1", text="Running plan", metadata={"type": "plan"})

        results = query_memory(user_id=10, query_text="running", where={"type": "session"})
        assert len(results) == 1
        assert results[0]["id"] == "s1"

    def test_query_respects_n_results(self):
        for i in range(10):
            add_memory(user_id=10, doc_id=f"d{i}", text=f"Workout number {i}")

        results = query_memory(user_id=10, query_text="workout", n_results=3)
        assert len(results) == 3


class TestDeleteMemory:
    def test_delete_removes_document(self):
        add_memory(user_id=10, doc_id="del_1", text="To be deleted")
        delete_memory(user_id=10, doc_id="del_1")
        results = query_memory(user_id=10, query_text="deleted")
        assert len(results) == 0


class TestDeleteCollection:
    def test_delete_user_collection_removes_all(self):
        add_memory(user_id=10, doc_id="c1", text="Some data")
        delete_user_collection(user_id=10)
        # After deletion, querying should return empty (new collection is auto-created on query)
        results = query_memory(user_id=10, query_text="data")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------

class TestBatchOperations:
    def test_batch_upsert(self):
        ids = ["b1", "b2", "b3"]
        texts = ["Squats and deadlifts", "HIIT cardio blast", "Yoga stretches"]
        metas = [{"type": "session"}, {"type": "session"}, {"type": "session"}]

        add_memories_batch(user_id=10, doc_ids=ids, texts=texts, metadatas=metas)
        results = query_memory(user_id=10, query_text="strength training", n_results=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Convenience ingestors
# ---------------------------------------------------------------------------

class TestConvenienceIngestors:
    def test_ingest_session_memory(self):
        ingest_session_memory(user_id=10, session_id=42, notes="Heavy squats 5x5", date_str="2026-10-20")
        results = query_memory(user_id=10, query_text="squats")
        assert len(results) == 1
        assert results[0]["id"] == "session_42"
        assert results[0]["metadata"]["type"] == "session"

    def test_ingest_plan_memory(self):
        ingest_plan_memory(user_id=10, plan_id=7, plan_text="4-week hypertrophy block focusing on progressive overload")
        results = query_memory(user_id=10, query_text="hypertrophy progressive overload")
        assert len(results) == 1
        assert results[0]["id"] == "plan_7"
        assert results[0]["metadata"]["type"] == "plan"


# ---------------------------------------------------------------------------
# Isolation
# ---------------------------------------------------------------------------

class TestUserIsolation:
    def test_memories_are_isolated_per_user(self):
        add_memory(user_id=1, doc_id="u1d1", text="User 1 bench press")
        add_memory(user_id=2, doc_id="u2d1", text="User 2 yoga")

        r1 = query_memory(user_id=1, query_text="bench")
        r2 = query_memory(user_id=2, query_text="bench")

        assert len(r1) == 1
        assert r1[0]["id"] == "u1d1"
        # User 2 has no bench press doc
        assert all("bench press" not in r["document"] for r in r2)
