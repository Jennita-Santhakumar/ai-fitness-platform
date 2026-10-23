"""
Tests for Day 20: Strava OAuth Integration.
All HTTP calls to Strava are mocked with unittest.mock — no real network I/O.
"""
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.services.strava import (
    disconnect_strava,
    generate_authorization_url,
    refresh_strava_token_if_expired,
    save_strava_tokens,
    verify_oauth_state,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_strava_user(db, suffix: str = "strava") -> User:
    """Create and persist a test user with no Strava tokens."""
    user = User(
        email=f"strava_{suffix}@test.com",
        hashed_password=hash_password("Password123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_connected_user(db, suffix: str = "connected") -> User:
    """Create and persist a user with Strava tokens already stored."""
    user = make_strava_user(db, suffix=suffix)
    user.strava_athlete_id = 99001
    user.strava_access_token = "access_abc"
    user.strava_refresh_token = "refresh_xyz"
    user.strava_expires_at = int(time.time()) + 21600  # 6 h from now
    user.strava_scope = "read,activity:read_all"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_and_login(client, suffix: str) -> dict:
    """Register a user and return Bearer auth headers."""
    email = f"strava_{suffix}@test.com"
    password = "Password123!"
    client.post("/auth/register", json={"email": email, "password": password})
    resp = client.post("/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_state(user_id: int, ttl_minutes: int = 15) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "strava_oauth",
        "exp": now + timedelta(minutes=ttl_minutes),
        "iat": now,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Unit tests — service layer
# ---------------------------------------------------------------------------

class TestGenerateAuthorizationUrl:
    def test_returns_strava_authorize_url(self):
        url = generate_authorization_url(user_id=42)
        assert "www.strava.com/oauth/authorize" in url

    def test_url_contains_client_id(self):
        url = generate_authorization_url(user_id=1)
        assert f"client_id={settings.STRAVA_CLIENT_ID}" in url

    def test_url_contains_state_param(self):
        url = generate_authorization_url(user_id=7)
        assert "state=" in url

    def test_url_contains_scope(self):
        url = generate_authorization_url(user_id=3)
        assert "scope=read" in url


class TestVerifyOAuthState:
    def test_valid_state_returns_user_id(self):
        state = _make_state(user_id=55)
        assert verify_oauth_state(state) == 55

    def test_expired_state_raises(self):
        state = _make_state(user_id=1, ttl_minutes=-1)
        with pytest.raises(ValueError, match="Invalid or expired"):
            verify_oauth_state(state)

    def test_wrong_type_raises(self):
        payload = {
            "sub": "10",
            "type": "wrong_type",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
            "iat": datetime.now(timezone.utc),
        }
        state = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        with pytest.raises(ValueError):
            verify_oauth_state(state)

    def test_garbage_state_raises(self):
        with pytest.raises(ValueError):
            verify_oauth_state("not.a.jwt.token")


class TestSaveStravaTokens:
    def test_saves_all_token_fields(self, db_session):
        user = make_strava_user(db_session, suffix="save_tok")
        token_data = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires_at": 9999999,
            "athlete": {"id": 12345},
        }
        updated = save_strava_tokens(db_session, user, token_data, scope="read")
        assert updated.strava_access_token == "new_access"
        assert updated.strava_refresh_token == "new_refresh"
        assert updated.strava_expires_at == 9999999
        assert updated.strava_athlete_id == 12345
        assert updated.strava_scope == "read"

    def test_saves_without_athlete(self, db_session):
        user = make_strava_user(db_session, suffix="no_athlete")
        token_data = {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_at": 111,
        }
        updated = save_strava_tokens(db_session, user, token_data)
        assert updated.strava_access_token == "tok"
        assert updated.strava_athlete_id is None


class TestDisconnectStrava:
    def test_clears_all_fields(self, db_session):
        user = make_connected_user(db_session, suffix="disc")
        with patch("app.services.strava.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client_cls.return_value = mock_client
            disconnect_strava(db_session, user)

        assert user.strava_access_token is None
        assert user.strava_refresh_token is None
        assert user.strava_athlete_id is None
        assert user.strava_expires_at is None
        assert user.strava_scope is None

    def test_survives_deauthorize_http_error(self, db_session):
        """Network failure during deauthorize should not prevent DB cleanup."""
        user = make_connected_user(db_session, suffix="disc_err")
        with patch("app.services.strava.httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.post.side_effect = Exception("network error")
            mock_client_cls.return_value = mock_client
            disconnect_strava(db_session, user)  # should not raise

        assert user.strava_access_token is None


class TestRefreshStravaToken:
    def test_returns_existing_token_when_not_expired(self, db_session):
        user = make_connected_user(db_session, suffix="refresh_valid")
        result = refresh_strava_token_if_expired(db_session, user)
        assert result == "access_abc"

    def test_returns_none_when_not_connected(self, db_session):
        user = make_strava_user(db_session, suffix="refresh_none")
        result = refresh_strava_token_if_expired(db_session, user)
        assert result is None

    def test_refreshes_expired_token(self, db_session):
        user = make_connected_user(db_session, suffix="refresh_exp")
        user.strava_expires_at = int(time.time()) - 100  # already expired
        db_session.commit()

        new_tokens = {
            "access_token": "fresh_access",
            "refresh_token": "fresh_refresh",
            "expires_at": int(time.time()) + 21600,
        }

        with patch("app.services.strava.httpx.Client") as mock_cls:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = new_tokens
            mock_http.post.return_value = mock_resp
            mock_cls.return_value = mock_http

            result = refresh_strava_token_if_expired(db_session, user)

        assert result == "fresh_access"
        assert user.strava_access_token == "fresh_access"

    def test_raises_on_refresh_failure(self, db_session):
        user = make_connected_user(db_session, suffix="refresh_fail")
        user.strava_expires_at = int(time.time()) - 100
        db_session.commit()

        with patch("app.services.strava.httpx.Client") as mock_cls:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"
            mock_http.post.return_value = mock_resp
            mock_cls.return_value = mock_http

            with pytest.raises(RuntimeError):
                refresh_strava_token_if_expired(db_session, user)


# ---------------------------------------------------------------------------
# API endpoint tests (use conftest `client` fixture)
# ---------------------------------------------------------------------------

class TestStravaConnectEndpoint:
    def test_connect_returns_auth_url(self, client):
        headers = register_and_login(client, suffix="ep_conn")
        resp = client.get("/integrations/strava/connect", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "authorization_url" in body
        assert "strava.com" in body["authorization_url"]

    def test_connect_requires_auth(self, client):
        resp = client.get("/integrations/strava/connect")
        assert resp.status_code == 401

    def test_connect_redirect_mode(self, client):
        headers = register_and_login(client, suffix="ep_redir")
        resp = client.get(
            "/integrations/strava/connect?redirect=true",
            headers=headers,
            follow_redirects=False,
        )
        assert resp.status_code == 307
        assert "strava.com" in resp.headers.get("location", "")


class TestStravaCallbackEndpoint:
    def test_callback_missing_state_returns_400(self, client):
        resp = client.get("/integrations/strava/callback?code=abc123")
        assert resp.status_code == 400

    def test_callback_invalid_state_returns_400(self, client):
        resp = client.get("/integrations/strava/callback?code=abc123&state=garbage")
        assert resp.status_code == 400

    def test_callback_success(self, client, db_session):
        user = make_strava_user(db_session, suffix="cb_ok")
        state = _make_state(user_id=user.id)

        token_response = {
            "access_token": "at_ok",
            "refresh_token": "rt_ok",
            "expires_at": int(time.time()) + 21600,
            "athlete": {"id": 77001},
        }

        with patch("app.api.strava.exchange_code_for_tokens", return_value=token_response):
            resp = client.get(
                f"/integrations/strava/callback?code=testcode&state={state}&scope=read,activity:read_all"
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "connected"
        assert body["athlete_id"] == 77001

    def test_callback_exchange_failure_returns_502(self, client, db_session):
        user = make_strava_user(db_session, suffix="cb_fail")
        state = _make_state(user_id=user.id)

        with patch("app.api.strava.exchange_code_for_tokens", side_effect=Exception("Strava down")):
            resp = client.get(f"/integrations/strava/callback?code=bad&state={state}")

        assert resp.status_code == 502


class TestStravaStatusEndpoint:
    def test_status_not_connected(self, client):
        headers = register_and_login(client, suffix="ep_stat")
        resp = client.get("/integrations/strava/status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False
        assert body["athlete_id"] is None

    def test_status_requires_auth(self, client):
        resp = client.get("/integrations/strava/status")
        assert resp.status_code == 401


class TestStravaDisconnectEndpoint:
    def test_disconnect_not_connected_returns_200(self, client):
        headers = register_and_login(client, suffix="ep_disc")
        resp = client.post("/integrations/strava/disconnect", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"

    def test_disconnect_requires_auth(self, client):
        resp = client.post("/integrations/strava/disconnect")
        assert resp.status_code == 401
