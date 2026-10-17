from unittest.mock import patch
import pytest

from app.schemas.plan import Plan


def sample_valid_plan_obj():
    return Plan.model_validate({
        "goal": "Strength",
        "level": "Intermediate",
        "weeks": [
            {
                "number": 1,
                "days": [
                    {
                        "name": "Day 1",
                        "focus": "Full Body",
                        "exercises": [{"name": "Squat", "sets": 3, "reps": 8, "rest_sec": 90}],
                    }
                ],
            }
        ],
    })


@patch("app.api.plans.generate_plan_with_failover")
def test_generate_and_fetch_plan_flow(mock_gen, client, auth_headers):
    """Verify full flow: generate, persist in DB, and re-fetch via GET /plans/{id}."""
    mock_gen.return_value = (sample_valid_plan_obj(), "groq", 0)
    headers = auth_headers("planner@example.com")

    # 1. POST /plans/generate
    payload = {
        "goal": "Strength",
        "level": "Intermediate",
        "equipment": "Full Gym",
        "days_per_week": 3,
        "weeks": 4,
        "injuries": "None",
    }
    resp = client.post("/plans/generate", json=payload, headers=headers)
    assert resp.status_code == 201
    plan_data = resp.json()
    assert plan_data["provider"] == "groq"
    assert plan_data["inputs"]["goal"] == "Strength"
    assert plan_data["plan"]["goal"] == "Strength"
    assert plan_data["is_active"] is False
    plan_id = plan_data["id"]

    # 2. GET /plans
    list_resp = client.get("/plans", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["id"] == plan_id

    # 3. GET /plans/{id}
    get_resp = client.get(f"/plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == plan_id
    assert get_resp.json()["plan"]["weeks"][0]["days"][0]["exercises"][0]["name"] == "Squat"


@patch("app.api.plans.generate_plan_with_failover")
def test_plan_ownership_enforcement(mock_gen, client, auth_headers):
    """Verify User B cannot access User A's plan (returns 404)."""
    mock_gen.return_value = (sample_valid_plan_obj(), "groq", 0)
    headers_a = auth_headers("athlete_a@example.com")
    headers_b = auth_headers("athlete_b@example.com")

    # User A creates plan
    resp = client.post(
        "/plans/generate",
        json={"goal": "Strength", "level": "Intermediate", "weeks": 4},
        headers=headers_a,
    )
    plan_id = resp.json()["id"]

    # User B tries to fetch User A's plan -> 404
    resp_b = client.get(f"/plans/{plan_id}", headers=headers_b)
    assert resp_b.status_code == 404
    assert resp_b.json()["detail"] == "Plan not found"


def test_generate_plan_input_limits_enforced(client, auth_headers):
    """Verify input validation limits (max 12 weeks, max field length)."""
    headers = auth_headers("limittester@example.com")

    # Exceed max weeks (> 12)
    resp = client.post(
        "/plans/generate",
        json={"goal": "Strength", "level": "Intermediate", "weeks": 15},
        headers=headers,
    )
    assert resp.status_code == 422

    # Exceed injuries field length (> 500 chars)
    long_injuries = "a" * 501
    resp2 = client.post(
        "/plans/generate",
        json={"goal": "Strength", "level": "Intermediate", "injuries": long_injuries},
        headers=headers,
    )
    assert resp2.status_code == 422
