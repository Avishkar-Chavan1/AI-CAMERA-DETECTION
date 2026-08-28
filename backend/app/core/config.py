"""Environment-backed application and vision configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Settings for platform infrastructure and the Phase 2 vision runtime."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Industrial Safety AI Platform"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    log_json: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        validation_alias=AliasChoices("PORT", "API_PORT"),
    )

    vision_source: str | None = None
    vision_person_model: str = "yolo11n.pt"
    vision_ppe_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MODEL_PATH", "VISION_PPE_MODEL"),
    )
    vision_ppe_class_map: dict[str, str] | None = None
    vision_tracker: Literal["bytetrack.yaml", "botsort.yaml"] = "bytetrack.yaml"
    vision_confidence: float = Field(default=0.35, gt=0.0, le=1.0)
    vision_iou_threshold: float = Field(default=0.45, gt=0.0, le=1.0)
    vision_display: bool = True
    vision_window_name: str = "Industrial Safety AI - Phase 2"
    vision_ppe_min_confidence: float = Field(default=0.25, gt=0.0, le=1.0)
    vision_association_min_containment: float = Field(default=0.20, ge=0.0, le=1.0)
    api_max_image_bytes: int = Field(default=20_000_000, ge=1_000_000)
    api_max_video_bytes: int = Field(default=500_000_000, ge=1_000_000)
    api_max_video_frames: int = Field(default=10_000, ge=1)
    api_event_log_path: str = "runs/inference/events.db"
    api_cors_origins: list[str] = ["http://localhost:8501", "http://127.0.0.1:8501"]
    api_key: str | None = None
    api_auth_enabled: bool = False
    api_rate_limit: int = Field(default=30, ge=1)
    api_rate_window_seconds: int = Field(default=60, ge=1)
    api_inference_timeout_seconds: int = Field(default=300, ge=1)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate levels accepted by the standard logger."""
        normalized = value.upper()
        supported_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
        if normalized not in supported_levels:
            message = f"LOG_LEVEL must be one of {sorted(supported_levels)}"
            raise ValueError(message)
        return normalized

    @field_validator("vision_source", "vision_ppe_model", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: object) -> object:
        """Treat blank environment values as intentionally unset."""
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_validator("vision_ppe_class_map")
    @classmethod
    def validate_ppe_class_map(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        """Ensure a model mapping only targets PPE classes supported by the UI."""
        if value is None:
            return None

        canonical_classes = {"helmet", "vest", "shoes"}
        normalized = {
            model_label.strip().casefold(): ppe_type.strip().casefold()
            for model_label, ppe_type in value.items()
        }
        unsupported = set(normalized.values()) - canonical_classes
        if unsupported:
            message = f"VISION_PPE_CLASS_MAP has unsupported target classes: {sorted(unsupported)}"
            raise ValueError(message)
        if any(not label for label in normalized):
            raise ValueError("VISION_PPE_CLASS_MAP labels must not be empty")
        return normalized

    @model_validator(mode="after")
    def validate_ppe_model_configuration(self) -> "Settings":
        """Require explicit label semantics before a PPE model can be used."""
        if self.vision_ppe_model is None:
            return self
        if self.vision_ppe_class_map is None:
            raise ValueError("VISION_PPE_CLASS_MAP is required when VISION_PPE_MODEL is set")

        required_classes = {"helmet", "vest", "shoes"}
        configured_classes = set(self.vision_ppe_class_map.values())
        missing = required_classes - configured_classes
        if missing:
            message = f"VISION_PPE_CLASS_MAP is missing required classes: {sorted(missing)}"
            raise ValueError(message)
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide, immutable settings instance."""
    return Settings()
