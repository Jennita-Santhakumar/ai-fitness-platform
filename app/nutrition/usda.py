"""
USDA FoodData Central API client with Redis caching.
Provides search_food and get_nutrients with 1-day Redis caching.
"""
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("ai_fitness.nutrition.usda")

# 1 day cache TTL in seconds
REDIS_CACHE_TTL = 86400


def get_redis_client():
    """
    Returns a Redis client if Redis is available, otherwise None.
    Catches connection issues defensively so app doesn't crash if Redis is down.
    """
    try:
        from redis import Redis
        client = Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        return client
    except Exception as exc:
        logger.debug(f"Redis not available for nutrition caching: {exc}")
        return None


def extract_macros(nutrients: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Extracts macronutrients (calories, protein, carbs, fat) from a USDA nutrients list.
    Supports both:
      1. Search format: items with 'nutrientName'/'nutrientNumber' and 'value'
      2. Food details format: items with nested 'nutrient' object and 'amount'
    """
    macros = {
        "calories": 0.0,
        "protein": 0.0,
        "carbs": 0.0,
        "fat": 0.0,
    }

    for item in nutrients:
        # Check nested nutrient object vs flat dictionary
        if "nutrient" in item and isinstance(item["nutrient"], dict):
            name = item["nutrient"].get("name", "").lower()
            number = str(item["nutrient"].get("number", ""))
            amount = item.get("amount", 0.0) or 0.0
        else:
            name = item.get("nutrientName", "").lower()
            number = str(item.get("nutrientNumber", ""))
            amount = item.get("value", 0.0) or 0.0

        try:
            val = float(amount)
        except (ValueError, TypeError):
            val = 0.0

        # Energy / Calories: KCAL
        if ("energy" in name and "kj" not in name) or number in ("208", "1008"):
            macros["calories"] = round(val, 1)
        # Protein
        elif "protein" in name or number in ("203", "1003"):
            macros["protein"] = round(val, 1)
        # Total Carbohydrate
        elif ("carbohydrate" in name) or number in ("205", "1005"):
            macros["carbs"] = round(val, 1)
        # Total Lipid / Fat
        elif ("total lipid" in name or name == "fat, total" or (name.startswith("fat") and "fatty" not in name)) or number in ("204", "1004"):
            macros["fat"] = round(val, 1)

    return macros


def search_food(
    query: str,
    page_size: int = 25,
    redis_client: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Searches foods in USDA FoodData Central.
    Checks Redis cache first. If missed, queries USDA API and caches for 1 day.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    cache_key = f"usda:search:{cleaned_query.lower()}"
    redis = redis_client if redis_client is not None else get_redis_client()

    # 1. Check Redis cache
    if redis is not None:
        try:
            cached_bytes = redis.get(cache_key)
            if cached_bytes:
                cached_data = json.loads(cached_bytes)
                logger.debug(f"Cache hit for search query: '{cleaned_query}'")
                return cached_data
        except Exception as exc:
            logger.warning(f"Redis get failed for key {cache_key}: {exc}")

    # 2. Call USDA FoodData Central Search API
    url = f"{settings.USDA_BASE_URL}/foods/search"
    params = {
        "query": cleaned_query,
        "pageSize": page_size,
        "api_key": settings.USDA_API_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error(f"Failed to query USDA FoodData Central: {exc}")
        raise

    foods = data.get("foods", [])
    results: List[Dict[str, Any]] = []

    for food in foods:
        fdc_id = food.get("fdcId")
        description = food.get("description", "Unknown food")
        serving_size = food.get("servingSize")
        serving_unit = food.get("servingSizeUnit")
        nutrients = food.get("foodNutrients", [])

        macros = extract_macros(nutrients)

        results.append({
            "fdc_id": fdc_id,
            "name": description,
            "calories": macros["calories"],
            "protein": macros["protein"],
            "carbs": macros["carbs"],
            "fat": macros["fat"],
            "serving_size": float(serving_size) if serving_size is not None else None,
            "serving_unit": serving_unit,
        })

    # 3. Store in Redis cache with 1 day TTL
    if redis is not None:
        try:
            redis.set(cache_key, json.dumps(results), ex=REDIS_CACHE_TTL)
        except Exception as exc:
            logger.warning(f"Redis set failed for key {cache_key}: {exc}")

    return results


def get_nutrients(
    fdc_id: int,
    redis_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Fetches macronutrient details for a specific food by USDA FDC ID.
    Checks Redis cache first, caching for 1 day on miss.
    """
    cache_key = f"usda:food:{fdc_id}"
    redis = redis_client if redis_client is not None else get_redis_client()

    # 1. Check Redis cache
    if redis is not None:
        try:
            cached_bytes = redis.get(cache_key)
            if cached_bytes:
                cached_data = json.loads(cached_bytes)
                logger.debug(f"Cache hit for food FDC ID: {fdc_id}")
                return cached_data
        except Exception as exc:
            logger.warning(f"Redis get failed for key {cache_key}: {exc}")

    # 2. Call USDA Food details API
    url = f"{settings.USDA_BASE_URL}/food/{fdc_id}"
    params = {
        "api_key": settings.USDA_API_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        logger.error(f"Failed to fetch food details for FDC ID {fdc_id}: {exc}")
        raise

    description = data.get("description", f"Food #{fdc_id}")
    nutrients = data.get("foodNutrients", [])
    macros = extract_macros(nutrients)

    result = {
        "fdc_id": fdc_id,
        "name": description,
        "calories": macros["calories"],
        "protein": macros["protein"],
        "carbs": macros["carbs"],
        "fat": macros["fat"],
    }

    # 3. Store in Redis cache
    if redis is not None:
        try:
            redis.set(cache_key, json.dumps(result), ex=REDIS_CACHE_TTL)
        except Exception as exc:
            logger.warning(f"Redis set failed for key {cache_key}: {exc}")

    return result
