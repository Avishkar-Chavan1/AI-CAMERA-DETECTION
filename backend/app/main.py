"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure process-level dependencies around the application lifecycle."""
    settings: Settings = app.state.settings
    configure_logging(settings)
    logger = get_logger(__name__)
    logger.info("application_started", extra={"environment": settings.app_env})
    yield
    logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API application without starting a server."""
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title=resolved_settings.app_name,
        version="0.2.0",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings

    @app.get("/health", tags=["platform"])
    async def health_check() -> dict[str, str]:
        """Report that the API process is available."""
        return {"status": "ok", "environment": resolved_settings.app_env}

    return app


app = create_app()
