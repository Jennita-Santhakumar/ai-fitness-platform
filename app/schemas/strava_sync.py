"""Strava schemas for activity sync (Day 21)."""
from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class StravaActivityItem(BaseModel):
    """A single Strava activity as returned by Strava's /athlete/activities API."""
    id: int
    name: str
    sport_type: Optional[str] = None
    start_date_local: Optional[str] = None  # ISO 8601 date string
    elapsed_time: Optional[int] = None       # seconds
    moving_time: Optional[int] = None        # seconds
    distance: Optional[float] = None         # metres
    total_elevation_gain: Optional[float] = None
    average_heartrate: Optional[float] = None
    max_heartrate: Optional[float] = None
    kilojoules: Optional[float] = None       # for rides


class StravaSyncResponse(BaseModel):
    """Result of a Strava activity sync operation."""
    synced: int
    skipped: int
    errors: int
    message: str
