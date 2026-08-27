"""Command-line entry point for the API service."""

import uvicorn

from backend.app.core.config import get_settings


def run() -> None:
    """Start the API using the configured network binding."""
    settings = get_settings()
    uvicorn.run(
        "backend.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
    )
