"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import configure_logging, get_logger
from backend.app.api.routes import router
from vision.inference import PpeInferenceEngine
from vision.event_log import EventLogger

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure process-level dependencies around the application lifecycle."""
    settings: Settings = app.state.settings
    configure_logging(settings)
    model_path = Path(settings.vision_ppe_model or "best.pt")
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    app.state.engine = None
    app.state.model_error = None
    try:
        app.state.engine = PpeInferenceEngine(
            model_path, settings.vision_ppe_min_confidence, settings.vision_iou_threshold
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        app.state.model_error = str(error)
        get_logger(__name__).error("model_load_failed", extra={"error": str(error)})
    event_path = Path(settings.api_event_log_path)
    if not event_path.is_absolute():
        event_path = PROJECT_ROOT / event_path
    app.state.event_logger = EventLogger(event_path)
    app.state.rate_limits = {}
    app.state.metrics = {"inference_requests": 0, "inference_errors": 0, "inference_seconds": 0.0}
    logger = get_logger(__name__)
    logger.info(
        "application_started",
        extra={"environment": settings.app_env, "model_loaded": app.state.engine is not None},
    )
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.api_cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.middleware("http")
    async def request_logging(request, call_next):
        started = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            get_logger(__name__).exception("request_failed", extra={"path": request.url.path})
            raise
        elapsed = perf_counter() - started
        get_logger(__name__).info(
            "request_completed",
            extra={"path": request.url.path, "status_code": response.status_code, "duration_seconds": round(elapsed, 4)},
        )
        response.headers["X-Process-Time-Ms"] = str(round(elapsed * 1000, 2))
        return response

    @app.get("/health", tags=["platform"])
    async def health_check() -> dict[str, str]:
        """Report that the API process is available."""
        return {"status": "ok", "environment": resolved_settings.app_env}

    return app


app = create_app()
