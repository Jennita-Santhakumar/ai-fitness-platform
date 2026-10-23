from datetime import date as dt_date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MacroNutrients(BaseModel):
    """Macronutrient profile for a food item or serving."""
    calories: float = Field(default=0.0, ge=0, description="Energy in kcal")
    protein: float = Field(default=0.0, ge=0, description="Protein in grams")
    carbs: float = Field(default=0.0, ge=0, description="Total carbohydrates in grams")
    fat: float = Field(default=0.0, ge=0, description="Total lipid (fat) in grams")


class FoodSearchResultItem(BaseModel):
    """A single food item returned from search."""
    fdc_id: int = Field(..., description="USDA FoodData Central unique identifier")
    name: str = Field(..., description="Description / common name of the food")
    calories: float = Field(default=0.0, ge=0, description="Calories in kcal per 100g or serving")
    protein: float = Field(default=0.0, ge=0, description="Protein in grams")
    carbs: float = Field(default=0.0, ge=0, description="Carbohydrates in grams")
    fat: float = Field(default=0.0, ge=0, description="Fat in grams")
    serving_size: Optional[float] = Field(None, description="Serving size amount if available")
    serving_unit: Optional[str] = Field(None, description="Serving size unit (e.g. g, ml, cup)")


class FoodSearchResponse(BaseModel):
    """Response envelope for food search queries."""
    query: str = Field(..., description="The query string that was searched")
    results: List[FoodSearchResultItem] = Field(default_factory=list, description="List of matching food items")
    total_hits: int = Field(default=0, ge=0, description="Total search matches found")


class FoodLogCreate(BaseModel):
    """Payload for logging a food item eaten."""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the food")
    grams: float = Field(..., gt=0, description="Serving quantity in grams")
    calories: float = Field(default=0.0, ge=0, description="Total energy in kcal")
    protein: float = Field(default=0.0, ge=0, description="Protein in grams")
    carbs: float = Field(default=0.0, ge=0, description="Carbohydrates in grams")
    fat: float = Field(default=0.0, ge=0, description="Fat in grams")
    date: Optional[dt_date] = Field(None, description="Date consumed (defaults to current date)")
    fdc_id: Optional[int] = Field(None, description="Optional USDA FDC identifier")


class FoodLogRead(BaseModel):
    """Response representation of a logged food item."""
    id: int
    user_id: int
    fdc_id: Optional[int] = None
    name: str
    grams: float
    calories: float
    protein: float
    carbs: float
    fat: float
    date: dt_date
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DailyNutritionSummary(BaseModel):
    """Aggregated daily totals for calories and macronutrients."""
    date: dt_date
    total_calories: float = 0.0
    total_protein: float = 0.0
    total_carbs: float = 0.0
    total_fat: float = 0.0
    item_count: int = 0
