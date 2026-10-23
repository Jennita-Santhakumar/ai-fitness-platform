"""
Tests for Day 21: Strava Activity Sync.
Tests the sync service layer, the Celery tasks, and the POST /integrations/strava/sync endpoint.
All Strava HTTP calls are mocked.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.security import hash_password
from app.models.session import WorkoutSession
from app.models.user import User
from app.services.strava_sync import (
    _activity_to_session_kwargs,
    _parse_activity_date,
    fetch_strava_activities,
    sync_strava_activities,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ACTIVITY = {
    "id": 9900001,
    "name": "Morning Run",
    "sport_type": "Run",
    "start_date_local": "2026-10-20T07:00:00",
    "elapsed_time": 2700,  # 45 min
    "moving_time": 2650,
    "distance": 7500.0,
    "total_elevation_gain": 42.0,
    "average_heartrate": 155.0,
    "max_heartrate": 178.0,
}

SAMPLE_ACTIVITY_2 = {
    "id": 9900002,
    "name": "Evening Yoga",
    "sport_type": "Yoga",
    "start_date_local": "2026-10-20T18:00:00",
    "elapsed_time": 3600,
    "moving_time": 3600,
    "distance": 0,
}


def _make_user(db, suffix="sync") -> User:
    user = User(
        email=f"strava_sync_{suffix}@test.com",
        hashed_password=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_connected_user(db, suffix="sync_conn") -> User:
    user = _make_user(db, suffix=suffix)
    user.strava_athlete_id = 88001
    user.strava_access_token = "valid_access_token"
    user.strava_refresh_token = "valid_refresh_token"
    user.strava_expires_at = int(time.time()) + 21600
    user.strava_scope = "read,activity:read_all"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _mock_httpx_get(activities_page1, activities_page2=None):
    """Create a mock httpx.Client context manager. Page 1 returns activities_page1, page 2 returns activities_page2 (default [])."""
    if activities_page2 is None:
        activities_page2 = []

    mock_cls = MagicMock()
    mock_http = MagicMock()
    mock_http.__enter__ = MagicMock(return_value=mock_http)
    mock_http.__exit__ = MagicMock(return_value=False)

    # Track call count to return different pages
    call_count = {"n": 0}
    pages = [activities_page1, activities_page2]

    def _get_side_effect(*args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        idx = min(call_count["n"], len(pages) - 1)
        resp.json.return_value = pages[idx]
        call_count["n"] += 1
        return resp

    mock_http.get.side_effect = _get_side_effect

    # Also mock POST for token refresh
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "access_token": "refreshed_access",
        "refresh_token": "refreshed_refresh",
        "expires_at": int(time.time()) + 21600,
    }
    mock_http.post.return_value = mock_post_resp
    mock_cls.return_value = mock_http
    return mock_cls


# ---------------------------------------------------------------------------
# Unit tests — parsing helpers
# ---------------------------------------------------------------------------

class TestParseActivityDate:
    def test_valid_iso_date(self):
        d = _parse_activity_date("2026-10-20T07:00:00")
        assert str(d) == "2026-10-20"

    def test_none_returns_today(self):
        from datetime import date
        d = _parse_activity_date(None)
        assert d == date.today()

    def test_garbage_returns_today(self):
        from datetime import date
        d = _parse_activity_date("not-a-date")
        assert d == date.today()


class TestActivityToSessionKwargs:
    def test_maps_all_fields(self):
        kwargs = _activity_to_session_kwargs(SAMPLE_ACTIVITY, user_id=42)
        assert kwargs["user_id"] == 42
        assert kwargs["strava_activity_id"] == 9900001
        assert kwargs["duration_min"] == 45
        assert "Morning Run" in kwargs["notes"]
        assert "7.50 km" in kwargs["notes"]

    def test_minimum_duration_is_1(self):
        activity = {"id": 1, "name": "Quick", "elapsed_time": 10}
        kwargs = _activity_to_session_kwargs(activity, user_id=1)
        assert kwargs["duration_min"] >= 1


# ---------------------------------------------------------------------------
# Unit tests — fetch_strava_activities
# ---------------------------------------------------------------------------

class TestFetchStravaActivities:
    def test_success(self):
        with patch("app.services.strava_sync.httpx.Client") as mock_cls:
            mock_cls_inst = _mock_httpx_get([SAMPLE_ACTIVITY])
            mock_http = mock_cls_inst.return_value
            mock_cls.return_value = mock_http

            result = fetch_strava_activities("fake_token", page=1, per_page=50)

        assert len(result) == 1
        assert result[0]["id"] == 9900001

    def test_401_raises_runtime_error(self):
        with patch("app.services.strava_sync.httpx.Client") as mock_cls:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"
            mock_http.get.return_value = mock_resp
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError, match="unauthorized"):
                fetch_strava_activities("bad_token")


# ---------------------------------------------------------------------------
# Integration tests — sync_strava_activities
# ---------------------------------------------------------------------------

class TestSyncStravaActivities:
    def test_imports_new_activities(self, db_session):
        user = _make_connected_user(db_session, suffix="sync_new")

        with patch("app.services.strava_sync.httpx.Client") as mock_cls:
            mock_inst = _mock_httpx_get([SAMPLE_ACTIVITY, SAMPLE_ACTIVITY_2])
            mock_cls.return_value = mock_inst.return_value

            synced, skipped, errors = sync_strava_activities(db_session, user)

        assert synced == 2
        assert skipped == 0
        assert errors == 0

        sessions = db_session.query(WorkoutSession).filter(
            WorkoutSession.user_id == user.id
        ).all()
        assert len(sessions) == 2
        strava_ids = {s.strava_activity_id for s in sessions}
        assert strava_ids == {9900001, 9900002}

    def test_skips_duplicates(self, db_session):
        from datetime import date as dt_date

        user = _make_connected_user(db_session, suffix="sync_dup")

        # Pre-insert one session
        existing = WorkoutSession(
            user_id=user.id,
            date=dt_date(2026, 10, 20),
            duration_min=45,
            strava_activity_id=9900001,
        )
        db_session.add(existing)
        db_session.commit()

        with patch("app.services.strava_sync.httpx.Client") as mock_cls:
            mock_inst = _mock_httpx_get([SAMPLE_ACTIVITY, SAMPLE_ACTIVITY_2])
            mock_cls.return_value = mock_inst.return_value

            synced, skipped, errors = sync_strava_activities(db_session, user)

        assert synced == 1  # only SAMPLE_ACTIVITY_2
        assert skipped == 1  # SAMPLE_ACTIVITY was duplicate

    def test_raises_for_unconnected_user(self, db_session):
        user = _make_user(db_session, suffix="sync_noconn")
        with pytest.raises(ValueError, match="no Strava connection"):
            sync_strava_activities(db_session, user)

    def test_empty_page_stops_sync(self, db_session):
        user = _make_connected_user(db_session, suffix="sync_empty")

        with patch("app.services.strava_sync.httpx.Client") as mock_cls:
            mock_inst = _mock_httpx_get([])  # empty activity list
            mock_cls.return_value = mock_inst.return_value

            synced, skipped, errors = sync_strava_activities(db_session, user)

        assert synced == 0
        assert skipped == 0
        assert errors == 0


# ---------------------------------------------------------------------------
# Celery task tests
# ---------------------------------------------------------------------------

class TestSyncUserStravaTask:
    def test_task_calls_sync(self, db_session):
        from app.worker import sync_user_strava_activities

        user = _make_connected_user(db_session, suffix="task_sync")

        with patch("app.services.strava_sync.sync_strava_activities", return_value=(3, 1, 0)) as mock_sync:
            result = sync_user_strava_activities(user.id)

        assert result["status"] == "success"
        assert result["synced"] == 3
        assert result["skipped"] == 1

    def test_task_skips_unconnected(self, db_session):
        from app.worker import sync_user_strava_activities

        user = _make_user(db_session, suffix="task_no_conn")
        result = sync_user_strava_activities(user.id)
        assert result["status"] == "skipped"


class TestSyncAllStravaTask:
    def test_task_processes_connected_users(self, db_session):
        from app.worker import sync_all_strava_activities

        user = _make_connected_user(db_session, suffix="task_all")

        with patch("app.services.strava_sync.sync_strava_activities", return_value=(5, 0, 0)):
            result = sync_all_strava_activities()

        assert result["status"] == "success"
        assert result["users_processed"] >= 1
        assert result["total_synced"] >= 5


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def _register_and_login(client, suffix: str) -> dict:
    email = f"strava_sync_{suffix}@test.com"
    password = "Password123!"
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


class TestStravaSyncEndpoint:
    def test_sync_requires_auth(self, client):
        resp = client.post("/integrations/strava/sync")
        assert resp.status_code == 401

    def test_sync_no_connection_returns_400(self, client):
        headers = _register_and_login(client, suffix="ep_sync_noconn")
        resp = client.post("/integrations/strava/sync", headers=headers)
        assert resp.status_code == 400
        assert "No Strava account" in resp.json()["detail"]

    def test_sync_success(self, client, db_session):
        # Create user via API
        email = "strava_sync_ep_ok@test.com"
        password = "Password123!"
        client.post("/auth/register", json={"email": email, "password": password})
        login = client.post("/auth/login", data={"username": email, "password": password})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Manually add Strava tokens to user in DB
        user = db_session.query(User).filter(User.email == email).first()
        user.strava_access_token = "valid"
        user.strava_refresh_token = "valid"
        user.strava_expires_at = int(time.time()) + 21600
        user.strava_athlete_id = 55001
        db_session.commit()

        with patch("app.api.strava.sync_strava_activities", return_value=(2, 0, 0)):
            resp = client.post("/integrations/strava/sync", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["synced"] == 2
        assert body["skipped"] == 0
        assert "Imported 2" in body["message"]
