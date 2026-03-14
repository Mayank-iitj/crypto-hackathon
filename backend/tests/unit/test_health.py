from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app import main


def test_health_check_returns_service_metadata():
    init_database = AsyncMock()
    close_database = AsyncMock()

    with patch.object(main, "init_database", init_database), patch.object(main, "close_database", close_database):
        with TestClient(main.create_app()) as client:
            response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "healthy"
    assert payload["service"] == "Q-Shield"
    assert payload["environment"] == "development"
    init_database.assert_awaited_once()
    close_database.assert_awaited_once()