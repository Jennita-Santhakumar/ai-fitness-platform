import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import httpx
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger("ai_fitness.strava")

STRAVA_AUTH_BASE = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_DEAUTHORIZE_URL = "https://www.strava.com/oauth/deauthorize"
DEFAULT_STRAVA_SCOPE = "read,activity:read_all"


def generate_authorization_url(user_id: int) -> str:
    """
    Constructs the Strava OAuth authorization URL with a cryptographically signed state token.
    The state token prevents CSRF and securely conveys the user ID to the callback.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "strava_oauth",
        "exp": now + timedelta(minutes=15),
        "iat": now,
    }
    state = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    params = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "redirect_uri": settings.STRAVA_REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": DEFAULT_STRAVA_SCOPE,
        "state": state,
    }
    req = httpx.Request("GET", STRAVA_AUTH_BASE, params=params)
    return str(req.url)


def verify_oauth_state(state: str) -> int:
    """
    Validates the state parameter returned by Strava, returning the authenticated user_id.
    Raises ValueError if the signature is invalid or expired.
    """
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "strava_oauth":
            raise ValueError("Invalid OAuth state type")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as err:
        logger.warning(f"OAuth state validation failed: {err}")
        raise ValueError("Invalid or expired OAuth state") from err


def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """
    Exchanges an authorization code for access and refresh tokens with Strava.
    """
    payload = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(STRAVA_TOKEN_URL, data=payload)
        if resp.status_code != 200:
            logger.error(f"Strava token exchange failed [{resp.status_code}]: {resp.text}")
            raise RuntimeError(f"Strava token exchange failed with status {resp.status_code}")
        return resp.json()


def save_strava_tokens(
    db: Session,
    user: User,
    token_data: Dict[str, Any],
    scope: Optional[str] = None,
) -> User:
    """
    Persists Strava OAuth credentials into the User database record.
    """
    user.strava_access_token = token_data.get("access_token")
    user.strava_refresh_token = token_data.get("refresh_token")
    user.strava_expires_at = token_data.get("expires_at")
    
    athlete = token_data.get("athlete")
    if isinstance(athlete, dict) and "id" in athlete:
        user.strava_athlete_id = athlete["id"]
        
    if scope:
        user.strava_scope = scope

    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Successfully saved Strava tokens for user_id={user.id}, athlete_id={user.strava_athlete_id}")
    return user


def refresh_strava_token_if_expired(
    db: Session,
    user: User,
    buffer_seconds: int = 300,
) -> Optional[str]:
    """
    Checks if the user's Strava access token is expired (or close to expiring within buffer_seconds).
    If expired, uses the refresh token to request a fresh token pair and updates the database.
    Returns a valid access token or None if not connected.
    """
    if not user.strava_access_token or not user.strava_refresh_token:
        return None

    current_time = int(time.time())
    expires_at = user.strava_expires_at or 0

    if current_time < (expires_at - buffer_seconds):
        # Current token is still valid
        return user.strava_access_token

    logger.info(f"Refreshing expired Strava token for user_id={user.id} (expires_at={expires_at})")
    payload = {
        "client_id": settings.STRAVA_CLIENT_ID,
        "client_secret": settings.STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": user.strava_refresh_token,
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(STRAVA_TOKEN_URL, data=payload)
            if resp.status_code != 200:
                logger.error(f"Strava token refresh failed [{resp.status_code}]: {resp.text}")
                raise RuntimeError(f"Strava token refresh failed: {resp.text}")
            new_tokens = resp.json()

        user.strava_access_token = new_tokens.get("access_token")
        user.strava_refresh_token = new_tokens.get("refresh_token", user.strava_refresh_token)
        user.strava_expires_at = new_tokens.get("expires_at")

        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Strava token renewed successfully for user_id={user.id}, new_expires_at={user.strava_expires_at}")
        return user.strava_access_token
    except Exception as exc:
        logger.error(f"Failed to refresh Strava token for user_id={user.id}: {exc}")
        raise exc


def disconnect_strava(db: Session, user: User) -> None:
    """
    Revokes the Strava access token and wipes OAuth credentials from the user record.
    """
    if user.strava_access_token:
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    STRAVA_DEAUTHORIZE_URL,
                    headers={"Authorization": f"Bearer {user.strava_access_token}"},
                )
        except Exception as exc:
            logger.warning(f"Error calling Strava deauthorize: {exc}")

    user.strava_athlete_id = None
    user.strava_access_token = None
    user.strava_refresh_token = None
    user.strava_expires_at = None
    user.strava_scope = None

    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Disconnected Strava account for user_id={user.id}")
