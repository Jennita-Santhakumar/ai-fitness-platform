import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.models.user import User
from app.nutrition.usda import search_food
from app.schemas.nutrition import FoodSearchResponse, FoodSearchResultItem

logger = logging.getLogger("ai_fitness.api.nutrition")

router = APIRouter(prefix="/nutrition", tags=["Nutrition"])


@router.get(
    "/search",
    response_model=FoodSearchResponse,
    summary="Search food database for nutritional info and macros",
    description="Queries USDA FoodData Central for foods matching the query and returns macronutrient data (calories, protein, carbs, fat). Results are cached for 1 day.",
)
def search_nutrition(
    q: str = Query(..., min_length=1, description="Food query string, e.g. 'banana'"),
    limit: int = Query(default=25, ge=1, le=50, description="Maximum number of items to return"),
    current_user: User = Depends(get_current_user),
):
    """
    Searches USDA FoodData Central and returns calories and macronutrients for matching items.
    """
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query 'q' cannot be empty or blank whitespace.",
        )

    try:
        results_data = search_food(query=clean_q, page_size=limit)
    except Exception as exc:
        logger.error(f"Error executing nutrition search for query '{clean_q}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to query USDA FoodData Central service: {str(exc)}",
        )

    items = [FoodSearchResultItem(**item) for item in results_data]
    return FoodSearchResponse(
        query=clean_q,
        results=items,
        total_hits=len(items),
    )
