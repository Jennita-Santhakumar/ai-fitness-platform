from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base schema with shared user attributes."""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for incoming user registration request."""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserRead(UserBase):
    """Schema for outgoing user representation (never exposes password hash)."""
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Schema for returning access and refresh tokens upon login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    """Schema for returning newly issued access token upon refresh."""
    access_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Schema for incoming token refresh request."""
    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for decoded token claims."""
    sub: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[int] = None
