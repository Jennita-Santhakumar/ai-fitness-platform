import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.core.db import Base, get_db
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


def test_register_user_success():
    """1. Test successful registration returns 201 with user details."""
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
    """2. Test duplicate registration rejects with 409 Conflict."""
    payload = {"email": "duplicate@example.com", "password": "securepassword123"}
    first_resp = client.post("/auth/register", json=payload)
    assert first_resp.status_code == 201

    second_resp = client.post("/auth/register", json=payload)
    assert second_resp.status_code == 409
    assert "already registered" in second_resp.json()["detail"].lower()


def test_register_invalid_email_format():
    """3. Test invalid email format is rejected with validation error (422)."""
    response = client.post(
        "/auth/register",
        json={"email": "invalid-email-format", "password": "securepassword123"},
    )
    assert response.status_code == 422


def test_register_password_not_in_response():
    """4. Test that neither plain password nor hashed_password leak in response."""
    response = client.post(
        "/auth/register",
        json={"email": "private@example.com", "password": "mysecretpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "password" not in data
    assert "hashed_password" not in data
