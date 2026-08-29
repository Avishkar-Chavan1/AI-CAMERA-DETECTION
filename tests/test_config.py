import os

import pytest
from backend.app.core.config import Settings
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def clear_ambient_vision_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep developer camera settings from changing configuration unit tests."""
    for variable in tuple(os.environ):
        if variable.startswith("VISION_"):
            monkeypatch.delenv(variable, raising=False)


def test_settings_accept_environment_values() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        log_level="debug",
        api_port=9000,
    )

    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"
    assert settings.api_port == 9000
    assert settings.model_path == "best.pt"


def test_api_model_path_does_not_require_phase_two_class_mapping() -> None:
    settings = Settings(_env_file=None, model_path="best.pt")

    assert settings.model_path == "best.pt"


def test_settings_reject_invalid_log_level() -> None:
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(_env_file=None, log_level="verbose")


def test_settings_reject_invalid_port() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, api_port=0)


def test_settings_accept_ppe_model_with_explicit_class_mapping() -> None:
    settings = Settings(
        _env_file=None,
        vision_ppe_model="models/ppe.pt",
        vision_ppe_class_map={"hard_hat": "helmet", "vest": "vest", "boots": "shoes"},
    )

    assert settings.vision_ppe_class_map == {
        "hard_hat": "helmet",
        "vest": "vest",
        "boots": "shoes",
    }


def test_settings_reject_ppe_model_without_class_mapping() -> None:
    with pytest.raises(ValidationError, match="VISION_PPE_CLASS_MAP"):
        Settings(_env_file=None, vision_ppe_model="models/ppe.pt")
