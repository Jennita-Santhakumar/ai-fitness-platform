import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.strava import (
    StravaCallbackResponse,
    StravaConnectResponse,
    StravaDisconnectResponse,
    StravaStatusResponse,
)
from app.schemas.strava_sync import StravaSyncResponse
from app.services.strava import (
    disconnect_strava,
    exchange_code_for_tokens,
    generate_authorization_url,
    save_strava_tokens,
    verify_oauth_state,
)
from app.services.strava_sync import sync_strava_activities

logger = logging.getLogger("ai_fitness.api.strava")

router = APIRouter(prefix="/integrations/strava", tags=["Strava Integration"])


@router.get(
    "/connect",
    response_model=StravaConnectResponse,
    summary="Initiate Strava OAuth connection",
    description="Generates a Strava authorization URL with a secure state token. If redirect=true, redirects directly.",
)
def connect_strava(
    redirect: bool = Query(default=False, description="Whether to issue an HTTP 307 redirect instead of returning JSON"),
    current_user: User = Depends(get_current_user),
):
    """
    Initiates the Strava OAuth 2.0 flow by creating an authorization URL with signed state.
    """
    auth_url = generate_authorization_url(user_id=current_user.id)
    if redirect:
        return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    return StravaConnectResponse(authorization_url=auth_url)


@router.get(
    "/callback",
    response_model=StravaCallbackResponse,
    summary="Strava OAuth callback endpoint",
    description="Exchanges the temporary code for access and refresh tokens, linking Strava to the athlete's account.",
)
def strava_oauth_callback(
    code: str = Query(..., description="The authorization code issued by Strava"),
    state: Optional[str] = Query(None, description="The signed CSRF state token returned by Strava"),
    scope: Optional[str] = Query(None, description="Granted scope permissions"),
    db: Session = Depends(get_db),
):
    """
    OAuth 2.0 callback endpoint. Decodes the signed state to locate the user,
    exchanges the code for tokens, and persists them into PostgreSQL.
    """
    if not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required OAuth state parameter",
        )

    try:
        user_id = verify_oauth_state(state)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User associated with OAuth state does not exist",
        )

    try:
        token_data = exchange_code_for_tokens(code=code)
    except Exception as exc:
        logger.error(f"Failed to exchange Strava code for tokens: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to communicate with Strava authorization servers",
        )

    updated_user = save_strava_tokens(db=db, user=user, token_data=token_data, scope=scope)
    return StravaCallbackResponse(
        status="connected",
        athlete_id=updated_user.strava_athlete_id,
        expires_at=updated_user.strava_expires_at,
        scope=updated_user.strava_scope,
    )


@router.get(
    "/status",
    response_model=StravaStatusResponse,
    summary="Check Strava connection status",
    description="Returns whether the authenticated user has an active linked Strava account.",
)
def get_strava_status(
    current_user: User = Depends(get_current_user),
):
    """
    Returns connection details including athlete ID, granted scopes, and token expiry.
    """
    is_connected = bool(current_user.strava_access_token and current_user.strava_refresh_token)
    return StravaStatusResponse(
        connected=is_connected,
        athlete_id=current_user.strava_athlete_id if is_connected else None,
        expires_at=current_user.strava_expires_at if is_connected else None,
        scope=current_user.strava_scope if is_connected else None,
    )


@router.post(
    "/disconnect",
    response_model=StravaDisconnectResponse,
    summary="Disconnect Strava account",
    description="Deauthorizes and wipes Strava OAuth tokens from the authenticated user's record.",
)
def disconnect_strava_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unlinks Strava credentials and restores the account to an unintegrated state.
    """
    if not current_user.strava_access_token and not current_user.strava_athlete_id:
        return StravaDisconnectResponse(
            status="disconnected",
            message="No active Strava account was connected",
        )

    disconnect_strava(db=db, user=current_user)
    return StravaDisconnectResponse(
        status="disconnected",
        message="Strava account successfully unlinked",
    )


@router.post(
    "/sync",
    response_model=StravaSyncResponse,
    summary="Sync Strava activities",
    description="Fetches recent activities from Strava and imports them as workout sessions, skipping duplicates.",
)
def sync_strava_activities_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Synchronously fetches and imports the user's recent Strava activities.
    Skips any activities that have already been imported (by strava_activity_id).
    """
    if not current_user.strava_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Strava account connected. Use /integrations/strava/connect first.",
        )

    try:
        synced, skipped, errors = sync_strava_activities(db=db, user=current_user)
    except Exception as exc:
        logger.error(f"Strava sync failed for user {current_user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to sync activities from Strava",
        )

    return StravaSyncResponse(
        synced=synced,
        skipped=skipped,
        errors=errors,
        message=f"Imported {synced} activities, skipped {skipped} duplicates",
    )
