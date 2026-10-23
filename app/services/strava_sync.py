"""
Strava activity sync service (Day 21).

Fetches activities from GET /athlete/activities, maps each to a WorkoutSession,
and skips duplicates identified by strava_activity_id.
"""
import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.models.session import WorkoutSession
from app.models.user import User
from app.services.strava import refresh_strava_token_if_expired

logger = logging.getLogger("ai_fitness.strava_sync")

STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
_SPORT_TYPE_NOTES_MAP = {
    "Run": "Running",
    "Ride": "Cycling",
    "Swim": "Swimming",
    "Walk": "Walking",
    "Hike": "Hiking",
    "WeightTraining": "Weight Training",
    "Yoga": "Yoga",
    "Workout": "General Workout",
}


def _parse_activity_date(date_str: Optional[str]) -> date:
    """Parse ISO 8601 local date from Strava activity; fall back to today."""
    if date_str:
        try:
            return datetime.fromisoformat(date_str.rstrip("Z")).date()
        except ValueError:
            pass
    return date.today()


def _activity_to_session_kwargs(activity: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Map a Strava activity dict to WorkoutSession constructor kwargs."""
    sport = activity.get("sport_type") or activity.get("type") or "Workout"
    activity_name = activity.get("name", sport)
    sport_label = _SPORT_TYPE_NOTES_MAP.get(sport, sport)

    elapsed = activity.get("elapsed_time") or activity.get("moving_time") or 0
    duration_min = max(1, round(elapsed / 60))

    activity_date = _parse_activity_date(activity.get("start_date_local"))

    notes_parts = [f"Strava import: {activity_name} ({sport_label})"]
    if activity.get("distance"):
        notes_parts.append(f"Distance: {activity['distance'] / 1000:.2f} km")
    if activity.get("total_elevation_gain"):
        notes_parts.append(f"Elevation: {activity['total_elevation_gain']:.0f} m")
    if activity.get("average_heartrate"):
        notes_parts.append(f"Avg HR: {activity['average_heartrate']:.0f} bpm")

    return {
        "user_id": user_id,
        "date": activity_date,
        "duration_min": duration_min,
        "notes": " | ".join(notes_parts),
        "strava_activity_id": activity["id"],
    }


def fetch_strava_activities(
    access_token: str,
    page: int = 1,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    """
    Fetches a page of activities from the Strava API for the authenticated athlete.
    Returns the parsed JSON list.
    """
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"page": page, "per_page": per_page}

    with httpx.Client(timeout=15.0) as client:
        resp = client.get(STRAVA_ACTIVITIES_URL, headers=headers, params=params)
        if resp.status_code == 401:
            raise RuntimeError("Strava access token is unauthorized or expired")
        if resp.status_code != 200:
            logger.error(f"Strava /athlete/activities failed [{resp.status_code}]: {resp.text}")
            raise RuntimeError(f"Strava activities fetch failed with status {resp.status_code}")
        return resp.json()


def sync_strava_activities(db: Session, user: User) -> Tuple[int, int, int]:
    """
    Main sync orchestrator. Refreshes the token if needed, fetches up to 2 pages
    of activities (100 most recent), maps each to a WorkoutSession, and skips
    any that already exist (identified by strava_activity_id).

    Returns: (synced, skipped, errors)
    """
    if not user.strava_access_token:
        raise ValueError("User has no Strava connection")

    # Ensure access token is valid (auto-refresh if expiring soon)
    access_token = refresh_strava_token_if_expired(db=db, user=user)
    if not access_token:
        raise ValueError("Failed to obtain a valid Strava access token")

    synced = skipped = errors = 0

    for page in range(1, 3):  # fetch up to 2 pages = 100 activities
        try:
            activities = fetch_strava_activities(access_token, page=page, per_page=50)
        except RuntimeError as exc:
            logger.error(f"Error fetching Strava activities page {page}: {exc}")
            errors += 1
            break

        if not activities:
            break  # no more pages

        for activity in activities:
            strava_id = activity.get("id")
            if not strava_id:
                errors += 1
                continue

            # Skip if already imported
            existing = (
                db.query(WorkoutSession)
                .filter(WorkoutSession.strava_activity_id == strava_id)
                .first()
            )
            if existing:
                skipped += 1
                continue

            try:
                kwargs = _activity_to_session_kwargs(activity, user_id=user.id)
                session = WorkoutSession(**kwargs)
                db.add(session)
                db.flush()
                synced += 1
            except Exception as exc:
                logger.error(f"Error mapping Strava activity {strava_id}: {exc}")
                errors += 1

    db.commit()
    logger.info(f"Strava sync for user {user.id}: synced={synced} skipped={skipped} errors={errors}")
    return synced, skipped, errors
