from backend.app.core.config import Settings
from backend.app.main import create_app
from fastapi.testclient import TestClient


def test_health_check_reports_process_availability() -> None:
    app = create_app(Settings(app_env="test"))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "test"}
