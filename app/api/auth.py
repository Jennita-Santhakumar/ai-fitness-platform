from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user with an email and password. Rejects duplicate emails with HTTP 409 Conflict.",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with bcrypt password hashing."""
    # Check if a user with this email already exists
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered. Please log in or use a different email.",
        )

    # Hash the password and create the user record
    hashed_pwd = hash_password(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user
