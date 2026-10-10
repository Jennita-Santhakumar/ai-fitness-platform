from datetime import datetime
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
