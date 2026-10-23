from typing import Optional
from pydantic import BaseModel, Field


class StravaConnectResponse(BaseModel):
    authorization_url: str = Field(..., description="Strava OAuth 2.0 authorization URL to redirect the user to")


class StravaCallbackResponse(BaseModel):
    status: str = Field("connected", description="Connection status message")
    athlete_id: Optional[int] = Field(None, description="Strava athlete identifier")
    expires_at: Optional[int] = Field(None, description="Access token expiration UNIX epoch timestamp")
    scope: Optional[str] = Field(None, description="Granted OAuth scopes")


class StravaStatusResponse(BaseModel):
    connected: bool = Field(..., description="Whether the athlete has an active connected Strava account")
    athlete_id: Optional[int] = Field(None, description="Strava athlete identifier if connected")
    expires_at: Optional[int] = Field(None, description="Access token expiration UNIX epoch timestamp")
    scope: Optional[str] = Field(None, description="Granted OAuth scopes")


class StravaDisconnectResponse(BaseModel):
    status: str = Field("disconnected", description="Disconnection status message")
    message: str = Field(..., description="Descriptive status details")
