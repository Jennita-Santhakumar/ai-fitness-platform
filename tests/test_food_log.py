"""
Tests for Day 25: Nutrition Log and Daily Summary.
Tests POST /nutrition/logs, GET /nutrition/logs, DELETE /nutrition/logs/{id},
and GET /nutrition/summary with ownership isolation and aggregation checks.
"""
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.models.food_log import FoodLog


# ---------------------------------------------------------------------------
# Test Food Logging CRUD
# ---------------------------------------------------------------------------

class TestFoodLogCRUD:
    """Test creating, listing, and deleting food log entries."""

    def test_create_food_log(self, client: TestClient, auth_headers):
        headers = auth_headers("foodie1@example.com")
        payload = {
            "name": "Oatmeal with Whey",
            "grams": 150.0,
            "calories": 350.0,
            "protein": 30.0,
            "carbs": 45.0,
            "fat": 5.0,
            "date": "2026-10-24",
            "fdc_id": 12345,
        }

        res = client.post("/nutrition/logs", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["id"] is not None
        assert data["name"] == "Oatmeal with Whey"
        assert data["calories"] == 350.0
        assert data["protein"] == 30.0
        assert data["carbs"] == 45.0
        assert data["fat"] == 5.0
        assert data["date"] == "2026-10-24"
        assert data["fdc_id"] == 12345

    def test_create_food_log_defaults_to_today(self, client: TestClient, auth_headers):
        headers = auth_headers("foodie2@example.com")
        payload = {
            "name": "Apple",
            "grams": 100.0,
            "calories": 52.0,
            "protein": 0.3,
            "carbs": 14.0,
            "fat": 0.2,
        }

        res = client.post("/nutrition/logs", json=payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["date"] == date.today().isoformat()

    def test_list_food_logs_filtered_by_date(self, client: TestClient, auth_headers):
        headers = auth_headers("foodie3@example.com")

        # Create 2 logs on 2026-10-24 and 1 on 2026-10-25
        client.post(
            "/nutrition/logs",
            json={"name": "Egg", "grams": 50, "calories": 70, "protein": 6, "carbs": 0.5, "fat": 5, "date": "2026-10-24"},
            headers=headers,
        )
        client.post(
            "/nutrition/logs",
            json={"name": "Toast", "grams": 40, "calories": 100, "protein": 3, "carbs": 20, "fat": 1, "date": "2026-10-24"},
            headers=headers,
        )
        client.post(
            "/nutrition/logs",
            json={"name": "Salmon", "grams": 200, "calories": 400, "protein": 40, "carbs": 0, "fat": 25, "date": "2026-10-25"},
            headers=headers,
        )

        # Query for 2026-10-24
        res24 = client.get("/nutrition/logs?date=2026-10-24", headers=headers)
        assert res24.status_code == 200
        logs24 = res24.json()
        assert len(logs24) == 2
        names = {item["name"] for item in logs24}
        assert names == {"Egg", "Toast"}

        # Query for 2026-10-25
        res25 = client.get("/nutrition/logs?date=2026-10-25", headers=headers)
        assert res25.status_code == 200
        logs25 = res25.json()
        assert len(logs25) == 1
        assert logs25[0]["name"] == "Salmon"

    def test_delete_food_log(self, client: TestClient, auth_headers):
        headers = auth_headers("foodie4@example.com")
        post_res = client.post(
            "/nutrition/logs",
            json={"name": "Banana", "grams": 120, "calories": 105, "protein": 1.3, "carbs": 27, "fat": 0.3},
            headers=headers,
        )
        log_id = post_res.json()["id"]

        del_res = client.delete(f"/nutrition/logs/{log_id}", headers=headers)
        assert del_res.status_code in [200, 204]

        # Verify it's gone
        list_res = client.get("/nutrition/logs", headers=headers)
        assert all(item["id"] != log_id for item in list_res.json())


# ---------------------------------------------------------------------------
# Test Ownership Isolation
# ---------------------------------------------------------------------------

class TestFoodLogOwnership:
    """Verify that users cannot access or delete each other's food logs."""

    def test_cannot_read_or_delete_other_user_log(self, client: TestClient, auth_headers):
        headers_a = auth_headers("user_a@example.com")
        headers_b = auth_headers("user_b@example.com")

        # User A logs a food
        res = client.post(
            "/nutrition/logs",
            json={"name": "Protein Shake", "grams": 300, "calories": 200, "protein": 30, "carbs": 10, "fat": 2, "date": "2026-10-24"},
            headers=headers_a,
        )
        log_id = res.json()["id"]

        # User B lists logs for the same day -> should see empty
        list_b = client.get("/nutrition/logs?date=2026-10-24", headers=headers_b)
        assert list_b.status_code == 200
        assert len(list_b.json()) == 0

        # User B attempts to delete User A's log -> 404 Not Found
        del_b = client.delete(f"/nutrition/logs/{log_id}", headers=headers_b)
        assert del_b.status_code == 404


# ---------------------------------------------------------------------------
# Test Daily Summary
# ---------------------------------------------------------------------------

class TestDailyNutritionSummary:
    """Verify SQLAlchemy func.sum daily aggregation endpoint."""

    def test_daily_summary_sums_macros_correctly(self, client: TestClient, auth_headers):
        headers = auth_headers("macro_tracker@example.com")
        target_date = "2026-10-24"

        # Log Breakfast
        client.post(
            "/nutrition/logs",
            json={"name": "Eggs & Toast", "grams": 150, "calories": 300.0, "protein": 18.0, "carbs": 25.0, "fat": 12.0, "date": target_date},
            headers=headers,
        )
        # Log Lunch
        client.post(
            "/nutrition/logs",
            json={"name": "Chicken & Rice", "grams": 350, "calories": 550.0, "protein": 45.0, "carbs": 60.0, "fat": 8.0, "date": target_date},
            headers=headers,
        )
        # Log Dinner
        client.post(
            "/nutrition/logs",
            json={"name": "Greek Yogurt & Berries", "grams": 200, "calories": 180.0, "protein": 20.0, "carbs": 15.0, "fat": 2.0, "date": target_date},
            headers=headers,
        )

        res = client.get(f"/nutrition/summary?date={target_date}", headers=headers)
        assert res.status_code == 200
        summary = res.json()

        assert summary["date"] == target_date
        assert summary["item_count"] == 3
        assert summary["total_calories"] == 1030.0
        assert summary["total_protein"] == 83.0
        assert summary["total_carbs"] == 100.0
        assert summary["total_fat"] == 22.0

    def test_daily_summary_empty_day_returns_zeroes(self, client: TestClient, auth_headers):
        headers = auth_headers("clean_slate@example.com")
        res = client.get("/nutrition/summary?date=2026-10-20", headers=headers)

        assert res.status_code == 200
        summary = res.json()
        assert summary["date"] == "2026-10-20"
        assert summary["item_count"] == 0
        assert summary["total_calories"] == 0.0
        assert summary["total_protein"] == 0.0
        assert summary["total_carbs"] == 0.0
        assert summary["total_fat"] == 0.0
