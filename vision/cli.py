"""Local command-line entry point for the Phase 2 vision runtime."""

import logging

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging, get_logger
from pydantic import ValidationError

from vision.errors import VisionError
from vision.pipeline import VisionPipeline


def run() -> None:
    """Run one configured webcam or local-file processing session."""
    try:
        settings = get_settings()
        configure_logging(settings)
        logger = get_logger(__name__)
        logger.info("vision_run_started source=%s", settings.vision_source)
        summary = VisionPipeline.from_settings(settings).run()
        logger.info(
            "vision_run_completed frames_processed=%s stopped_by_user=%s",
            summary.frames_processed,
            summary.stopped_by_user,
        )
    except (ValidationError, VisionError) as error:
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger(__name__).error("vision_run_failed: %s", error)
        raise SystemExit(1) from error
