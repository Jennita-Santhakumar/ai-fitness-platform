import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.db import Base, get_db
from app.main import app

# Shared in-memory test database using StaticPool
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def db_session():
    """Recreate clean tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session):
    """Provide a TestClient that uses the shared in-memory test database."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Helper fixture to create a registered user and return valid auth headers."""
    def _auth_headers(email: str = "testathlete@example.com", password: str = "password12345"):
        client.post("/auth/register", json={"email": email, "password": password})
        login_res = client.post("/auth/login", data={"username": email, "password": password})
        token = login_res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return _auth_headers
