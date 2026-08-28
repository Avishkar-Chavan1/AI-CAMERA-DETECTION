from fastapi.testclient import TestClient
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.main import create_app


class FakeEngine:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass


def test_api_health_reports_model_loaded(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    app = create_app(Settings(_env_file=None, app_env="test"))
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_loaded": True}


def test_image_endpoint_rejects_non_image_upload(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    app = create_app(Settings(_env_file=None, app_env="test"))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/inference/image",
            files={"file": ("notes.txt", b"not an image", "text/plain")},
        )
    assert response.status_code == 415
    assert "JPEG" in response.json()["detail"]


def test_image_endpoint_rejects_oversized_upload(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    app = create_app(Settings(_env_file=None, app_env="test", api_max_image_bytes=1_000_000))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/inference/image",
            files={"file": ("large.jpg", b"x" * 1_000_001, "image/jpeg")},
        )
    assert response.status_code == 413


def test_image_endpoint_returns_structured_inference(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    monkeypatch.setattr(
        "backend.app.api.routes.frame_response",
        lambda *_args: {"detections": [], "workers": [], "summary": {
            "total_people": 0, "safe_workers": 0, "workers_with_violations": 0,
            "total_violations": 0, "violation_types": [],
        }},
    )
    app = create_app(Settings(_env_file=None, app_env="test"))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/inference/image",
            files={
                "file": (
                    "image.jpg",
                    Path("data/construction-ppe/test/images/image1.jpeg").read_bytes(),
                    "image/jpeg",
                )
            },
        )
    assert response.status_code == 200
    assert set(response.json()) == {"detections", "workers", "summary"}


def test_inference_requires_configured_api_key(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    app = create_app(Settings(_env_file=None, app_env="test", api_auth_enabled=True, api_key="secret"))
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/inference/image",
            files={"file": ("image.jpg", b"not an image", "image/jpeg")},
        )
    assert response.status_code == 401


def test_inference_accepts_api_key_and_enforces_rate_limit(monkeypatch) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    monkeypatch.setattr(
        "backend.app.api.routes.frame_response",
        lambda *_args: {"detections": [], "workers": [], "summary": {
            "total_people": 0, "safe_workers": 0, "workers_with_violations": 0,
            "total_violations": 0, "violation_types": [],
        }},
    )
    app = create_app(Settings(
        _env_file=None, app_env="test", api_auth_enabled=True, api_key="secret", api_rate_limit=1,
    ))
    upload = {"file": ("image.jpg", Path("data/construction-ppe/test/images/image1.jpeg").read_bytes(), "image/jpeg")}
    with TestClient(app) as client:
        first = client.post("/api/v1/inference/image", headers={"X-API-Key": "secret"}, files=upload)
        second = client.post("/api/v1/inference/image", headers={"X-API-Key": "secret"}, files=upload)
    assert first.status_code == 200
    assert second.status_code == 429


def test_events_endpoint_returns_persisted_events(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("backend.app.main.PpeInferenceEngine", FakeEngine)
    app = create_app(Settings(
        _env_file=None,
        app_env="test",
        api_event_log_path=str(tmp_path / "events.db"),
    ))
    with TestClient(app) as client:
        app.state.event_logger.record("image", ["person"], 0.8, "SAFE_OR_UNKNOWN", 0)
        response = client.get("/api/v1/events")

    assert response.status_code == 200
    assert response.json()["events"][0]["source_type"] == "image"
