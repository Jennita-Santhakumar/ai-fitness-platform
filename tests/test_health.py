from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.db import get_db

client = TestClient(app)


def test_health_check_success():
    """Verify that GET /health returns 200 and status ok when DB is healthy."""
    mock_db = MagicMock(spec=Session)
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}

    app.dependency_overrides.clear()


def test_health_check_database_failure():
    """Verify that GET /health returns 503 when the database fails."""
    mock_db = MagicMock(spec=Session)
    mock_db.execute.side_effect = Exception("Connection refused")
    app.dependency_overrides[get_db] = lambda: mock_db

    response = client.get("/health")
    assert response.status_code == 503
    assert "Database connection error" in response.json()["detail"]

    app.dependency_overrides.clear()
