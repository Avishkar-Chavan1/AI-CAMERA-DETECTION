"""Structured, stdout-only logging configuration."""

import json
import logging
import sys
from typing import Any

from backend.app.core.config import Settings


class JsonFormatter(logging.Formatter):
    """Render the standard log record fields as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "environment"):
            payload["environment"] = record.environment
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    """Configure the root logger once per process for local or container execution."""
    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for use by application modules."""
    return logging.getLogger(name)
