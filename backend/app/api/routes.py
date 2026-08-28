"""Versioned inference API routes."""

import tempfile
import hmac
import time
from typing import BinaryIO
from pathlib import Path

from fastapi import APIRouter, File, Header, HTTPException, Query, Request, Response, UploadFile

from backend.app.core.logging import get_logger
from backend.app.services.inference_service import frame_response

router = APIRouter(prefix="/api/v1", tags=["inference"])
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}
VIDEO_TYPES = {"video/mp4", "video/avi", "video/quicktime", "video/x-matroska", "video/webm"}


@router.get("/health")
async def api_health(request: Request) -> dict[str, object]:
    """Report API and model readiness."""
    model_loaded = request.app.state.engine is not None
    response: dict[str, object] = {
        "status": "ok" if model_loaded else "degraded",
        "model_loaded": model_loaded,
    }
    if not model_loaded:
        response["model_error"] = request.app.state.model_error or "Model is unavailable"
    return response


@router.get("/metrics")
async def metrics(request: Request) -> dict[str, object]:
    """Expose lightweight process metrics for basic monitoring."""
    return dict(request.app.state.metrics)


@router.get("/events")
async def recent_events(request: Request, limit: int = Query(100, ge=1, le=500)) -> dict[str, object]:
    """Return recent persisted inference events for the dashboard."""
    try:
        return {"events": request.app.state.event_logger.list_recent(limit)}
    except Exception as error:
        get_logger(__name__).exception("event_history_failed", extra={"error": str(error)})
        raise HTTPException(503, "Event history is temporarily unavailable") from error


@router.get("/ready", status_code=200)
async def readiness(request: Request, response: Response) -> dict[str, object]:
    """Report whether the service is ready to perform inference."""
    if request.app.state.engine is None:
        response.status_code = 503
        return {"status": "not_ready", "model_loaded": False}
    return {"status": "ready", "model_loaded": True}


@router.post("/inference/image")
async def image_inference(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
    confidence: float = Query(0.25, gt=0.0, le=1.0),
    iou: float = Query(0.45, gt=0.0, le=1.0),
) -> dict[str, object]:
    """Run inference on an uploaded image; no client path is accepted."""
    _authorize(request, x_api_key)
    _check_rate_limit(request)
    _require_model(request)
    if file.content_type not in IMAGE_TYPES:
        raise HTTPException(415, "Upload a JPEG, PNG, WEBP, or BMP image")
    _validate_extension(file.filename, {".jpg", ".jpeg", ".png", ".webp", ".bmp"})
    data = await _read_limited(file, request.app.state.settings.api_max_image_bytes)
    if not data:
        raise HTTPException(400, "Uploaded image is empty")
    try:
        import cv2
        import numpy as np

        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("image could not be decoded")
        started = time.perf_counter()
        response = frame_response(request.app.state.engine, frame, confidence, iou)
        elapsed = _record_timing(request, started)
        _enforce_timeout(request, elapsed)
        _log_event(request, "image", response)
        return response
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        _record_error(request)
        raise HTTPException(500, "Image inference failed") from error


@router.post("/inference/video")
async def video_inference(
    request: Request,
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
    confidence: float = Query(0.25, gt=0.0, le=1.0),
    iou: float = Query(0.45, gt=0.0, le=1.0),
) -> dict[str, object]:
    """Run inference on every frame of an uploaded video."""
    _authorize(request, x_api_key)
    _check_rate_limit(request)
    _require_model(request)
    if file.content_type not in VIDEO_TYPES:
        raise HTTPException(415, "Upload an MP4, AVI, MOV, MKV, or WEBM video")
    source_path: Path | None = None
    try:
        import cv2

        suffix = Path(file.filename or ".mp4").suffix.casefold()
        if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
            raise HTTPException(415, "Upload a supported video extension")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as source:
            await _write_limited(file, source, request.app.state.settings.api_max_video_bytes)
            source_path = Path(source.name)
        capture = cv2.VideoCapture(str(source_path))
        if not capture.isOpened():
            raise ValueError("video could not be opened")
        frames: list[dict[str, object]] = []
        video_started = time.perf_counter()
        truncated = False
        try:
            while len(frames) < request.app.state.settings.api_max_video_frames:
                success, frame = capture.read()
                if not success:
                    break
                started = time.perf_counter()
                response = frame_response(request.app.state.engine, frame, confidence, iou)
                elapsed = _record_timing(request, started)
                _enforce_timeout(request, elapsed)
                _log_event(request, "video", response)
                frames.append(response)
                if time.perf_counter() - video_started > request.app.state.settings.api_inference_timeout_seconds:
                    _record_error(request)
                    raise HTTPException(504, "Video inference exceeded the configured time limit")
            if len(frames) == request.app.state.settings.api_max_video_frames:
                truncated, _ = capture.read()
        finally:
            capture.release()
        if not frames:
            raise ValueError("video contains no readable frames")
        return {
            "frames": frames,
            "frame_count": len(frames),
            "truncated": truncated,
        }
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except HTTPException:
        raise
    except Exception as error:
        _record_error(request)
        raise HTTPException(500, "Video inference failed") from error
    finally:
        if source_path is not None:
            source_path.unlink(missing_ok=True)


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """Read an upload in chunks and reject it before unbounded memory use."""
    chunks: list[bytes] = []
    size = 0
    try:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f"Uploaded file exceeds the {limit} byte limit")
            chunks.append(chunk)
    finally:
        await file.close()
    return b"".join(chunks)


async def _write_limited(file: UploadFile, output: BinaryIO, limit: int) -> None:
    size = 0
    try:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise HTTPException(413, f"Uploaded file exceeds the {limit} byte limit")
            output.write(chunk)
    finally:
        await file.close()
    if size == 0:
        raise HTTPException(400, "Uploaded video is empty")


def _log_event(request: Request, source_type: str, response: dict[str, object]) -> None:
    summary = response["summary"]
    detections = response["detections"]
    if not isinstance(summary, dict) or not isinstance(detections, list):
        return
    confidences = [float(item["confidence"]) for item in detections if isinstance(item, dict)]
    try:
        request.app.state.event_logger.record(
            source_type,
            [str(item["class_name"]) for item in detections if isinstance(item, dict)],
            max(confidences, default=0.0),
            str(summary.get("status", "SAFE_OR_UNKNOWN")),
            int(summary["total_violations"]),
            [item for item in detections if isinstance(item, dict)],
        )
    except Exception as error:
        get_logger(__name__).exception("event_log_write_failed", extra={"error": str(error)})


def _require_model(request: Request) -> None:
    if request.app.state.engine is None:
        raise HTTPException(503, "Inference model is unavailable")


def _validate_extension(filename: str | None, allowed: set[str]) -> None:
    extension = Path(filename or "").suffix.casefold()
    if extension not in allowed:
        raise HTTPException(415, "File extension does not match a supported media type")


def _authorize(request: Request, api_key: str | None) -> None:
    settings = request.app.state.settings
    if settings.api_auth_enabled and (
        not settings.api_key or not api_key or not hmac.compare_digest(api_key, settings.api_key)
    ):
        raise HTTPException(401, "Valid API key required")


def _check_rate_limit(request: Request) -> None:
    now = time.monotonic()
    client = request.client.host if request.client else "unknown"
    limits = request.app.state.rate_limits
    timestamps = [stamp for stamp in limits.get(client, []) if now - stamp < request.app.state.settings.api_rate_window_seconds]
    if len(timestamps) >= request.app.state.settings.api_rate_limit:
        raise HTTPException(429, "Inference rate limit exceeded")
    timestamps.append(now)
    limits[client] = timestamps


def _record_timing(request: Request, started: float) -> float:
    elapsed = time.perf_counter() - started
    metrics = request.app.state.metrics
    metrics["inference_requests"] += 1
    metrics["inference_seconds"] += elapsed
    return elapsed


def _enforce_timeout(request: Request, elapsed: float) -> None:
    if elapsed > request.app.state.settings.api_inference_timeout_seconds:
        _record_error(request)
        raise HTTPException(504, "Inference exceeded the configured time limit")


def _record_error(request: Request) -> None:
    request.app.state.metrics["inference_errors"] += 1
