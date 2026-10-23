from datetime import date
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.food_log import FoodLog
from app.models.user import User
from app.nutrition.usda import search_food
from app.schemas.nutrition import (
    DailyNutritionSummary,
    FoodLogCreate,
    FoodLogRead,
    FoodSearchResponse,
    FoodSearchResultItem,
)

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


@router.post(
    "/logs",
    response_model=FoodLogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log a consumed food item",
    description="Creates a new food log entry with quantity, calories, and macronutrients for the authenticated user.",
)
def create_food_log(
    payload: FoodLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Logs food item consumed by user. Defaults to current date if none provided.
    """
    target_date = payload.date or date.today()
    log_entry = FoodLog(
        user_id=current_user.id,
        fdc_id=payload.fdc_id,
        name=payload.name,
        grams=payload.grams,
        calories=round(payload.calories, 1),
        protein=round(payload.protein, 1),
        carbs=round(payload.carbs, 1),
        fat=round(payload.fat, 1),
        date=target_date,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


@router.get(
    "/logs",
    response_model=List[FoodLogRead],
    summary="List logged food items",
    description="Retrieves food logs for the authenticated user, optionally filtered by date.",
)
def list_food_logs(
    date_val: Optional[date] = Query(None, alias="date", description="Filter logs by calendar date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists logged foods for the current user, optionally filtered by date.
    """
    stmt = select(FoodLog).where(FoodLog.user_id == current_user.id)
    if date_val:
        stmt = stmt.where(FoodLog.date == date_val)
    stmt = stmt.order_by(FoodLog.id.asc())
    return list(db.scalars(stmt).all())


@router.delete(
    "/logs/{log_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a logged food item",
    description="Deletes a food log entry owned by the authenticated user. Returns 404 if not found or unauthorized.",
)
def delete_food_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a food log entry with ownership isolation.
    """
    stmt = select(FoodLog).where(FoodLog.id == log_id, FoodLog.user_id == current_user.id)
    entry = db.scalars(stmt).first()
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Food log entry #{log_id} not found.",
        )
    db.delete(entry)
    db.commit()
    return {"message": "Food log deleted successfully", "id": log_id}


@router.get(
    "/summary",
    response_model=DailyNutritionSummary,
    summary="Get daily nutrition summary and aggregated totals",
    description="Aggregates calories, protein, carbs, and fat totals for a specific date using SQL func.sum.",
)
def get_daily_nutrition_summary(
    date_val: Optional[date] = Query(None, alias="date", description="Target calendar date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes daily totals for calories and macronutrients for the authenticated user.
    """
    target_date = date_val or date.today()
    stmt = (
        select(
            func.coalesce(func.sum(FoodLog.calories), 0.0).label("total_calories"),
            func.coalesce(func.sum(FoodLog.protein), 0.0).label("total_protein"),
            func.coalesce(func.sum(FoodLog.carbs), 0.0).label("total_carbs"),
            func.coalesce(func.sum(FoodLog.fat), 0.0).label("total_fat"),
            func.count(FoodLog.id).label("item_count"),
        )
        .where(FoodLog.user_id == current_user.id, FoodLog.date == target_date)
    )
    row = db.execute(stmt).one()

    return DailyNutritionSummary(
        date=target_date,
        total_calories=round(float(row.total_calories), 1),
        total_protein=round(float(row.total_protein), 1),
        total_carbs=round(float(row.total_carbs), 1),
        total_fat=round(float(row.total_fat), 1),
        item_count=int(row.item_count),
    )
