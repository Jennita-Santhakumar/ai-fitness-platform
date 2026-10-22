from unittest.mock import patch
import pytest

from app.schemas.plan import Plan
from app.worker import celery_app


def sample_valid_plan_obj():
    return Plan.model_validate({
        "goal": "Hypertrophy",
        "level": "Advanced",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Upper Body",
                        "exercises": [{"name": "Bench Press", "sets": 4, "reps": 8, "rest_sec": 120}],
                    }
                ],
            }
        ],
    })


def test_generate_plan_async_returns_202_accepted(eager_celery, client, auth_headers):
    """Verify POST /plans/generate-async returns HTTP 202 with task_id."""
    headers = auth_headers("asyncuser1@example.com")
    payload = {
        "goal": "Hypertrophy",
        "level": "Advanced",
        "equipment": "Full Gym",
        "days_per_week": 4,
        "weeks": 4,
    }

    with patch("app.worker.generate_plan_with_failover") as mock_gen:
        mock_gen.return_value = (sample_valid_plan_obj(), "groq", 0)
        response = client.post("/plans/generate-async", json=payload, headers=headers)

    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert len(data["task_id"]) > 0
    assert data["status"] == "pending"


def test_generate_plan_async_full_lifecycle_with_polling(eager_celery, client, auth_headers):
    """Verify end-to-end flow: async dispatch -> worker execution -> poll GET /tasks/{task_id} -> fetch plan."""
    headers = auth_headers("asyncuser2@example.com")
    payload = {
        "goal": "Hypertrophy",
        "level": "Advanced",
        "equipment": "Full Gym",
        "days_per_week": 3,
        "weeks": 2,
    }

    with patch("app.worker.generate_plan_with_failover") as mock_gen:
        mock_gen.return_value = (sample_valid_plan_obj(), "gemini", 1)
        resp = client.post("/plans/generate-async", json=payload, headers=headers)
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

    # Poll task status
    poll_resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert poll_resp.status_code == 200
    task_data = poll_resp.json()
    assert task_data["task_id"] == task_id
    assert task_data["status"] == "success"
    assert task_data["provider"] == "gemini"
    assert isinstance(task_data["plan_id"], int)

    # Fetch the generated plan record directly from GET /plans/{plan_id}
    plan_id = task_data["plan_id"]
    get_plan_resp = client.get(f"/plans/{plan_id}", headers=headers)
    assert get_plan_resp.status_code == 200
    saved_plan = get_plan_resp.json()
    assert saved_plan["id"] == plan_id
    assert saved_plan["provider"] == "gemini"
    assert saved_plan["plan"]["goal"] == "Hypertrophy"
    assert saved_plan["plan"]["weeks"][0]["days"][0]["exercises"][0]["name"] == "Bench Press"


def test_task_status_pending_state(eager_celery, client, auth_headers):
    """Verify polling an unstarted/pending task returns status='pending'."""
    headers = auth_headers("asyncuser3@example.com")
    resp = client.get("/tasks/non-existent-or-unstarted-task-id", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert resp.json()["plan_id"] is None


def test_task_failure_polling(eager_celery, client, auth_headers):
    """Verify Celery task failure is accurately reflected in GET /tasks/{task_id}."""
    headers = auth_headers("asyncuser4@example.com")
    payload = {
        "goal": "Hypertrophy",
        "level": "Advanced",
        "weeks": 4,
    }

    with patch("app.worker.generate_plan_with_failover", side_effect=RuntimeError("All LLM providers unavailable")):
        resp = client.post("/plans/generate-async", json=payload, headers=headers)
        assert resp.status_code == 202
        task_id = resp.json()["task_id"]

    # Poll status after worker failure
    poll_resp = client.get(f"/tasks/{task_id}", headers=headers)
    assert poll_resp.status_code == 200
    task_data = poll_resp.json()
    assert task_data["task_id"] == task_id
    assert task_data["status"] == "failure"
    assert "All LLM providers unavailable" in task_data["error"]
    assert task_data["plan_id"] is None


def test_generate_plan_async_validation_errors(client, auth_headers):
    """Verify Pydantic input validation blocks bad requests before queuing a task."""
    headers = auth_headers("asyncuser5@example.com")

    # Invalid weeks (> 12)
    resp = client.post(
        "/plans/generate-async",
        json={"goal": "Strength", "level": "Intermediate", "weeks": 20},
        headers=headers,
    )
    assert resp.status_code == 422


def test_async_endpoints_require_authentication(client):
    """Verify unauthenticated requests to async endpoints return 401."""
    resp_post = client.post("/plans/generate-async", json={"goal": "Strength", "level": "Intermediate", "weeks": 4})
    assert resp_post.status_code == 401

    resp_get = client.get("/tasks/dummy-task-id")
    assert resp_get.status_code == 401
