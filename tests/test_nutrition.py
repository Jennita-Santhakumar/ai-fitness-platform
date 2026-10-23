"""
Tests for Day 24: USDA Nutrition Client and Food Search.
Tests search_food, get_nutrients, macro extraction, Redis caching,
and the GET /nutrition/search endpoint.
All external HTTP and Redis calls are mocked.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.nutrition.usda import (
    extract_macros,
    get_nutrients,
    search_food,
)


# ---------------------------------------------------------------------------
# Sample Mock Data
# ---------------------------------------------------------------------------

SAMPLE_USDA_SEARCH_RESPONSE = {
    "totalHits": 2,
    "currentPage": 1,
    "totalPages": 1,
    "foods": [
        {
            "fdcId": 173944,
            "description": "Bananas, raw",
            "dataType": "Foundation",
            "servingSize": 100.0,
            "servingSizeUnit": "g",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "nutrientNumber": "208", "unitName": "KCAL", "value": 89.0},
                {"nutrientId": 1003, "nutrientName": "Protein", "nutrientNumber": "203", "unitName": "G", "value": 1.09},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "nutrientNumber": "205", "unitName": "G", "value": 22.84},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "nutrientNumber": "204", "unitName": "G", "value": 0.33},
            ],
        },
        {
            "fdcId": 173945,
            "description": "Banana chips",
            "dataType": "Survey (FNDDS)",
            "servingSize": 100.0,
            "servingSizeUnit": "g",
            "foodNutrients": [
                {"nutrientId": 1008, "nutrientName": "Energy", "nutrientNumber": "208", "unitName": "KCAL", "value": 519.0},
                {"nutrientId": 1003, "nutrientName": "Protein", "nutrientNumber": "203", "unitName": "G", "value": 2.3},
                {"nutrientId": 1005, "nutrientName": "Carbohydrate, by difference", "nutrientNumber": "205", "unitName": "G", "value": 58.4},
                {"nutrientId": 1004, "nutrientName": "Total lipid (fat)", "nutrientNumber": "204", "unitName": "G", "value": 33.6},
            ],
        },
    ],
}

SAMPLE_USDA_FOOD_DETAILS = {
    "fdcId": 173944,
    "description": "Bananas, raw",
    "dataType": "Foundation",
    "foodNutrients": [
        {
            "nutrient": {"id": 1008, "number": "208", "name": "Energy", "unitName": "kcal"},
            "amount": 89.0,
        },
        {
            "nutrient": {"id": 1003, "number": "203", "name": "Protein", "unitName": "g"},
            "amount": 1.09,
        },
        {
            "nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference", "unitName": "g"},
            "amount": 22.84,
        },
        {
            "nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "unitName": "g"},
            "amount": 0.33,
        },
    ],
}


# ---------------------------------------------------------------------------
# Test Macro Extraction
# ---------------------------------------------------------------------------

class TestExtractMacros:
    """Test macro extraction logic from USDA nutrient dictionaries."""

    def test_extract_macros_from_search_format(self):
        nutrients = SAMPLE_USDA_SEARCH_RESPONSE["foods"][0]["foodNutrients"]
        macros = extract_macros(nutrients)
        assert macros["calories"] == 89.0
        assert macros["protein"] == 1.1
        assert macros["carbs"] == 22.8
        assert macros["fat"] == 0.3

    def test_extract_macros_from_detail_format(self):
        nutrients = SAMPLE_USDA_FOOD_DETAILS["foodNutrients"]
        macros = extract_macros(nutrients)
        assert macros["calories"] == 89.0
        assert macros["protein"] == 1.1
        assert macros["carbs"] == 22.8
        assert macros["fat"] == 0.3

    def test_extract_macros_with_empty_or_missing_nutrients(self):
        macros = extract_macros([])
        assert macros == {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}

    def test_extract_macros_case_insensitive_matching(self):
        nutrients = [
            {"nutrientName": "ENERGY", "value": 150.0},
            {"nutrientName": "protein", "value": 15.5},
            {"nutrientName": "CARBOHYDRATE, TOTAL", "value": 10.0},
            {"nutrientName": "Fat, Total", "value": 5.0},
        ]
        macros = extract_macros(nutrients)
        assert macros["calories"] == 150.0
        assert macros["protein"] == 15.5
        assert macros["carbs"] == 10.0
        assert macros["fat"] == 5.0


# ---------------------------------------------------------------------------
# Test Search Food Client
# ---------------------------------------------------------------------------

class TestSearchFood:
    """Test search_food function with HTTP mocking and Redis caching."""

    @patch("app.nutrition.usda.httpx.get")
    def test_search_food_success_cache_miss(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_USDA_SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # Cache miss

        results = search_food("banana", redis_client=mock_redis)

        assert len(results) == 2
        assert results[0]["fdc_id"] == 173944
        assert results[0]["name"] == "Bananas, raw"
        assert results[0]["calories"] == 89.0
        assert results[0]["protein"] == 1.1
        assert results[0]["carbs"] == 22.8
        assert results[0]["fat"] == 0.3

        # Verify cached in Redis for 1 day (86400 seconds)
        mock_redis.setex.assert_called_once()
        args, kwargs = mock_redis.setex.call_args
        assert "usda:search:banana" in args[0]
        assert args[1] == 86400

    @patch("app.nutrition.usda.httpx.get")
    def test_search_food_cache_hit(self, mock_get):
        cached_data = [
            {
                "fdc_id": 173944,
                "name": "Bananas, raw",
                "calories": 89.0,
                "protein": 1.1,
                "carbs": 22.8,
                "fat": 0.3,
            }
        ]
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(cached_data).encode("utf-8")

        results = search_food("banana", redis_client=mock_redis)

        # HTTP should NOT have been called due to cache hit
        mock_get.assert_not_called()
        assert len(results) == 1
        assert results[0]["fdc_id"] == 173944
        assert results[0]["name"] == "Bananas, raw"

    @patch("app.nutrition.usda.httpx.get")
    def test_search_food_redis_connection_error_graceful_fallback(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_USDA_SEARCH_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis connection refused")

        # Should fall back to USDA API call gracefully without error
        results = search_food("banana", redis_client=mock_redis)
        assert len(results) == 2
        mock_get.assert_called_once()

    @patch("app.nutrition.usda.httpx.get")
    def test_search_food_empty_query_returns_empty_list(self, mock_get):
        results = search_food("   ")
        assert results == []
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Test Get Nutrients Client
# ---------------------------------------------------------------------------

class TestGetNutrients:
    """Test get_nutrients function for single food lookup."""

    @patch("app.nutrition.usda.httpx.get")
    def test_get_nutrients_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = SAMPLE_USDA_FOOD_DETAILS
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        food_info = get_nutrients(173944, redis_client=mock_redis)

        assert food_info["fdc_id"] == 173944
        assert food_info["name"] == "Bananas, raw"
        assert food_info["calories"] == 89.0
        assert food_info["protein"] == 1.1
        assert food_info["carbs"] == 22.8
        assert food_info["fat"] == 0.3

        # Verify Redis caching
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert "usda:food:173944" in args[0]
        assert args[1] == 86400

    @patch("app.nutrition.usda.httpx.get")
    def test_get_nutrients_cache_hit(self, mock_get):
        cached = {
            "fdc_id": 173944,
            "name": "Bananas, raw",
            "calories": 89.0,
            "protein": 1.1,
            "carbs": 22.8,
            "fat": 0.3,
        }
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(cached).encode("utf-8")

        result = get_nutrients(173944, redis_client=mock_redis)
        mock_get.assert_not_called()
        assert result == cached


# ---------------------------------------------------------------------------
# Test API Endpoint GET /nutrition/search
# ---------------------------------------------------------------------------

class TestNutritionSearchAPI:
    """Test FastAPI endpoint GET /nutrition/search?q="""

    @patch("app.api.nutrition.search_food")
    def test_search_endpoint_authenticated_success(self, mock_search, client: TestClient, auth_headers):
        mock_search.return_value = [
            {
                "fdc_id": 173944,
                "name": "Bananas, raw",
                "calories": 89.0,
                "protein": 1.1,
                "carbs": 22.8,
                "fat": 0.3,
                "serving_size": 100.0,
                "serving_unit": "g",
            }
        ]

        headers = auth_headers("nutritionuser@example.com")
        res = client.get("/nutrition/search?q=banana", headers=headers)

        assert res.status_code == 200
        data = res.json()
        assert data["query"] == "banana"
        assert len(data["results"]) == 1
        assert data["results"][0]["name"] == "Bananas, raw"
        assert data["results"][0]["calories"] == 89.0
        assert data["results"][0]["protein"] == 1.1
        assert data["results"][0]["carbs"] == 22.8
        assert data["results"][0]["fat"] == 0.3

    def test_search_endpoint_unauthorized(self, client: TestClient):
        res = client.get("/nutrition/search?q=banana")
        assert res.status_code == 401

    def test_search_endpoint_empty_query(self, client: TestClient, auth_headers):
        headers = auth_headers("nutuser2@example.com")
        res = client.get("/nutrition/search?q=", headers=headers)
        assert res.status_code in [400, 422]
