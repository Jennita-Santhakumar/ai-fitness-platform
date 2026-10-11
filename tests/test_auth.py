from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.core.security import create_access_token
from app.main import app

# Shared in-memory SQLite database using StaticPool for multi-threaded TestClient access
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# --- Day 4 Tests ---

def test_register_user_success():
    """Test successful registration returns 201 with user details."""
    response = client.post(
        "/auth/register",
        json={"email": "athlete@example.com", "password": "supersecretpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "athlete@example.com"
    assert "id" in data
    assert data["is_active"] is True


def test_register_duplicate_email_returns_409():
    """Test duplicate registration rejects with 409 Conflict."""
    payload = {"email": "duplicate@example.com", "password": "securepassword123"}
    first_resp = client.post("/auth/register", json=payload)
    assert first_resp.status_code == 201

    second_resp = client.post("/auth/register", json=payload)
    assert second_resp.status_code == 409
    assert "already registered" in second_resp.json()["detail"].lower()


def test_register_invalid_email_format():
    """Test invalid email format is rejected with validation error (422)."""
    response = client.post(
        "/auth/register",
        json={"email": "invalid-email-format", "password": "securepassword123"},
    )
    assert response.status_code == 422


def test_register_password_not_in_response():
    """Test that neither plain password nor hashed_password leak in response."""
    response = client.post(
        "/auth/register",
        json={"email": "private@example.com", "password": "mysecretpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "password" not in data
    assert "hashed_password" not in data


# --- Day 5 Tests ---

def test_login_success():
    """Test login with correct credentials returns access and refresh tokens."""
    client.post(
        "/auth/register",
        json={"email": "loginuser@example.com", "password": "password12345"},
    )
    response = client.post(
        "/auth/login",
        data={"username": "loginuser@example.com", "password": "password12345"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401():
    """Test login with incorrect password returns 401 Unauthorized."""
    client.post(
        "/auth/register",
        json={"email": "wrongpwd@example.com", "password": "correctpassword123"},
    )
    response = client.post(
        "/auth/login",
        data={"username": "wrongpwd@example.com", "password": "incorrectpassword"},
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_users_me_without_token_returns_401():
    """Test GET /users/me without Authorization header returns 401 Unauthorized."""
    response = client.get("/users/me")
    assert response.status_code == 401


def test_users_me_with_valid_token_returns_user():
    """Test GET /users/me with valid Bearer token returns authenticated user."""
    reg_resp = client.post(
        "/auth/register",
        json={"email": "me@example.com", "password": "password12345"},
    )
    login_resp = client.post(
        "/auth/login",
        data={"username": "me@example.com", "password": "password12345"},
    )
    token = login_resp.json()["access_token"]

    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
    assert response.json()["id"] == reg_resp.json()["id"]


def test_users_me_with_expired_token_returns_401():
    """Test GET /users/me with expired token returns 401 Unauthorized."""
    reg_resp = client.post(
        "/auth/register",
        json={"email": "expired@example.com", "password": "password12345"},
    )
    user_id = reg_resp.json()["id"]
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-1),  # Already expired in the past
    )
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "could not validate credentials" in response.json()["detail"].lower()


def test_refresh_token_exchange_success():
    """Test exchanging a valid refresh token for a new access token."""
    client.post(
        "/auth/register",
        json={"email": "refresher@example.com", "password": "password12345"},
    )
    login_resp = client.post(
        "/auth/login",
        data={"username": "refresher@example.com", "password": "password12345"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify that the newly issued access token works on /users/me
    me_resp = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "refresher@example.com"
