"""
End-to-End Integration Test for Milestone 4 (Day 29).
Executes the full user lifecycle:
1. Registration & Authentication
2. User profile retrieval
3. Strava OAuth status check
4. Workout session creation & listing
5. Memory-augmented workout plan generation
6. Food database search & food logging
7. Daily nutrition summary aggregation
8. Verification of data consistency and ownership
"""
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.llm.base import LLMProvider
from app.schemas.plan import Plan


class MockE2ELLM(LLMProvider):
    """Test double LLM returning a valid strict Plan."""
    def generate(self, prompt: str, system_prompt: str = None) -> str:
        plan = {
            "goal": "Strength",
            "level": "Intermediate",
            "weeks": [
                {
                    "number": 1,
                    "days": [
                        {
                            "name": "Day 1 - Push",
                            "focus": "Chest and Triceps",
                            "exercises": [
                                {"name": "Barbell Bench Press", "sets": 4, "reps": 8, "rest_sec": 90, "notes": "RPE 8"},
                                {"name": "Overhead Press", "sets": 3, "reps": 10, "rest_sec": 60, "notes": "Strict form"},
                            ],
                        }
                    ],
                }
            ],
        }
        return json.dumps(plan)


class TestFullEndToEndFlow:
    """Verifies that the entire application flows together smoothly."""

    @patch("app.nutrition.usda.httpx.get")
    def test_complete_platform_lifecycle(self, mock_usda_get, client: TestClient):
        # Setup USDA mock
        mock_usda_resp = MagicMock()
        mock_usda_resp.status_code = 200
        mock_usda_resp.json.return_value = {
            "totalHits": 1,
            "foods": [
                {
                    "fdcId": 999123,
                    "description": "Banana, raw",
                    "servingSize": 100.0,
                    "servingSizeUnit": "g",
                    "foodNutrients": [
                        {"nutrientNumber": "208", "nutrientName": "Energy", "value": 89.0},
                        {"nutrientNumber": "203", "nutrientName": "Protein", "value": 1.1},
                        {"nutrientNumber": "205", "nutrientName": "Carbohydrate, by difference", "value": 22.8},
                        {"nutrientNumber": "204", "nutrientName": "Total lipid (fat)", "value": 0.3},
                    ],
                }
            ],
        }
        mock_usda_resp.raise_for_status.return_value = None
        mock_usda_get.return_value = mock_usda_resp

        # 1. Register
        reg_res = client.post(
            "/auth/register",
            json={"email": "e2e_champion@example.com", "password": "supersecurepassword123"},
        )
        assert reg_res.status_code == 201

        # 2. Login
        login_res = client.post(
            "/auth/login",
            data={"username": "e2e_champion@example.com", "password": "supersecurepassword123"},
        )
        assert login_res.status_code == 200
        tokens = login_res.json()
        token = tokens["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get /users/me
        me_res = client.get("/users/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == "e2e_champion@example.com"

        # 4. Check Strava connection status
        strava_res = client.get("/integrations/strava/status", headers=headers)
        assert strava_res.status_code == 200
        assert strava_res.json()["connected"] is False

        # 5. Log a workout session
        session_res = client.post(
            "/sessions",
            json={"date": "2026-10-24", "duration_min": 50, "notes": "Heavy deadlifts and accessories"},
            headers=headers,
        )
        assert session_res.status_code == 201
        session_id = session_res.json()["id"]

        sessions_list_res = client.get("/sessions", headers=headers)
        assert sessions_list_res.status_code == 200
        assert any(s["id"] == session_id for s in sessions_list_res.json())

        # 6. Generate an AI Workout Plan with LLM provider mock
        from app.api.deps import get_llm_providers
        app_overrides = client.app.dependency_overrides
        app_overrides[get_llm_providers] = lambda: [MockE2ELLM()]

        try:
            plan_res = client.post(
                "/plans/generate",
                json={
                    "goal": "Strength",
                    "level": "Intermediate",
                    "equipment": "Full Gym",
                    "days_per_week": 3,
                    "weeks": 4,
                },
                headers=headers,
            )
            assert plan_res.status_code == 201
            plan_record = plan_res.json()
            assert plan_record["id"] is not None
            assert plan_record["plan"]["goal"] == "Strength"

            # Verify in plans list
            plans_list_res = client.get("/plans", headers=headers)
            assert plans_list_res.status_code == 200
            assert len(plans_list_res.json()) >= 1
        finally:
            app_overrides.pop(get_llm_providers, None)

        # 7. Search food in nutrition API
        search_res = client.get("/nutrition/search?q=banana", headers=headers)
        assert search_res.status_code == 200
        search_data = search_res.json()
        assert len(search_data["results"]) == 1
        assert search_data["results"][0]["name"] == "Banana, raw"

        # 8. Log food intake
        food_log_res = client.post(
            "/nutrition/logs",
            json={
                "name": "Banana, raw",
                "grams": 150.0,
                "calories": 133.5,
                "protein": 1.7,
                "carbs": 34.2,
                "fat": 0.5,
                "date": "2026-10-24",
                "fdc_id": 999123,
            },
            headers=headers,
        )
        assert food_log_res.status_code == 201

        # 9. Verify daily nutrition summary
        summary_res = client.get("/nutrition/summary?date=2026-10-24", headers=headers)
        assert summary_res.status_code == 200
        summary_data = summary_res.json()
        assert summary_data["date"] == "2026-10-24"
        assert summary_data["item_count"] == 1
        assert summary_data["total_calories"] == 133.5
        assert summary_data["total_protein"] == 1.7
        assert summary_data["total_carbs"] == 34.2
        assert summary_data["total_fat"] == 0.5
