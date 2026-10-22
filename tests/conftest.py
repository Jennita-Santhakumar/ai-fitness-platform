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

from app.core import db as core_db
from app import worker as app_worker
core_db.SessionLocal = TestingSessionLocal
app_worker.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def configure_celery_test_mode():
    """Ensure Celery always runs in-memory and in eager mode across all tests."""
    from app.worker import celery_app

    celery_app.conf.update(
        broker_url="memory://",
        result_backend="cache+memory://",
        task_always_eager=True,
        task_store_eager_result=True,
        task_eager_propagates=False,
    )
    celery_app.backend_cls = None
    celery_app._backend = celery_app._get_backend()
    for t in celery_app.tasks.values():
        t.store_eager_result = True

    yield celery_app


@pytest.fixture
def eager_celery(configure_celery_test_mode):
    """Provides celery_app for tests."""
    return configure_celery_test_mode


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
