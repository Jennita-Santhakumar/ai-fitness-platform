"""
Tests for Day 30: Targeted test coverage improvements.
Covers remaining edge cases across sessions, tasks, workouts, and nutrition.
"""
from datetime import date
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db


class TestSessionEdgeCases:
    """Covers session get, update, and error branches in app/api/sessions.py."""

    def test_get_session_by_id_and_not_found(self, client: TestClient, auth_headers):
        headers = auth_headers("sess_coverage@example.com")

        # Create session
        res = client.post(
            "/sessions",
            json={"date": "2026-10-24", "duration_min": 60, "notes": "Leg Day"},
            headers=headers,
        )
        assert res.status_code == 201
        session_id = res.json()["id"]

        # Get existing
        get_res = client.get(f"/sessions/{session_id}", headers=headers)
        assert get_res.status_code == 200
        assert get_res.json()["duration_min"] == 60

        # Get non-existent
        res_404 = client.get("/sessions/99999", headers=headers)
        assert res_404.status_code == 404

    def test_update_session_with_workout_validation(self, client: TestClient, auth_headers):
        headers = auth_headers("sess_updater@example.com")

        # 1. Create a workout
        w_res = client.post("/workouts", json={"title": "Upper Body", "notes": "A1"}, headers=headers)
        workout_id = w_res.json()["id"]

        # 2. Create session without workout
        s_res = client.post(
            "/sessions",
            json={"date": "2026-10-24", "duration_min": 45, "notes": "Solo Run"},
            headers=headers,
        )
        session_id = s_res.json()["id"]

        # 3. Update session attaching workout
        patch_res = client.patch(
            f"/sessions/{session_id}",
            json={"duration_min": 55, "workout_id": workout_id, "notes": "Updated upper day"},
            headers=headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["duration_min"] == 55
        assert patch_res.json()["workout_id"] == workout_id

        # 4. Update session referencing non-existent workout -> 404
        bad_patch = client.patch(
            f"/sessions/{session_id}",
            json={"workout_id": 99999},
            headers=headers,
        )
        assert bad_patch.status_code == 404

        # 5. Update non-existent session -> 404
        miss_patch = client.patch(
            "/sessions/99999",
            json={"duration_min": 30},
            headers=headers,
        )
        assert miss_patch.status_code == 404


class TestTaskStatusEndpoints:
    """Covers task status endpoint edge cases in app/api/tasks.py."""

    def test_get_task_status_lifecycle(self, client: TestClient, auth_headers):
        headers = auth_headers("task_tester@example.com")

        # Query non-existent or completed task
        with patch("app.api.tasks.AsyncResult") as mock_async_result:
            mock_task = MagicMock()
            mock_task.state = "PENDING"
            mock_task.result = None
            mock_async_result.return_value = mock_task

            res = client.get("/tasks/fake-task-id-123", headers=headers)
            assert res.status_code == 200
            assert res.json()["status"] == "pending"


class TestDatabaseSessionGenerator:
    """Covers get_db yield and close logic."""

    def test_get_db_generator(self):
        gen = get_db()
        db = next(gen)
        assert db is not None
        # Cleanly trigger generator close
        with pytest.raises(StopIteration):
            next(gen)
