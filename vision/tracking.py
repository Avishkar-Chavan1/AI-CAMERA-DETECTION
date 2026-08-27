"""Persistent worker tracking backed by Ultralytics ByteTrack or BoT-SORT."""

from collections.abc import Mapping
from typing import Any

from vision.errors import VisionModelError
from vision.models import BoundingBox, TrackedWorker


class UltralyticsPersonTracker:
    """Detect persons and persist their IDs across a single video source."""

    def __init__(
        self,
        model_reference: str,
        tracker_configuration: str,
        confidence: float,
        iou_threshold: float,
    ) -> None:
        self._model = self._load_model(model_reference)
        self._person_class_ids = self._find_person_class_ids(self._model.names)
        self._tracker_configuration = tracker_configuration
        self._confidence = confidence
        self._iou_threshold = iou_threshold

    @staticmethod
    def _load_model(model_reference: str) -> Any:
        try:
            from ultralytics import YOLO
        except ImportError as error:  # pragma: no cover - guarded by the vision extra
            message = "Ultralytics is unavailable. Install the project with the 'vision' extra."
            raise VisionModelError(message) from error

        try:
            return YOLO(model_reference)
        except Exception as error:  # pragma: no cover - depends on model weights and runtime
            raise VisionModelError(f"Unable to load person model: {model_reference!r}") from error

    @staticmethod
    def _find_person_class_ids(names: Any) -> list[int]:
        if isinstance(names, Mapping):
            labels = names.items()
        else:
            labels = enumerate(names)
        person_class_ids = [
            int(class_id) for class_id, name in labels if str(name).casefold() == "person"
        ]
        if not person_class_ids:
            raise VisionModelError(
                "The configured person model has no class named 'person'. "
                "Use a detector trained with an explicit person class."
            )
        return person_class_ids

    def track(self, frame: Any) -> list[TrackedWorker]:
        """Detect persons and retain the tracker state for the next frame."""
        try:
            result = self._model.track(
                source=frame,
                persist=True,
                tracker=self._tracker_configuration,
                classes=self._person_class_ids,
                conf=self._confidence,
                iou=self._iou_threshold,
                verbose=False,
            )[0]
        except Exception as error:  # pragma: no cover - depends on model runtime and hardware
            raise VisionModelError("Person detection and tracking inference failed") from error

        boxes = result.boxes
        if boxes is None or boxes.id is None:
            return []

        coordinates = boxes.xyxy.cpu().tolist()
        confidences = boxes.conf.cpu().tolist()
        worker_ids = boxes.id.int().cpu().tolist()
        return [
            TrackedWorker(
                worker_id=int(worker_id),
                bounding_box=BoundingBox(*map(float, xyxy)),
                confidence=float(confidence),
            )
            for worker_id, confidence, xyxy in zip(
                worker_ids, confidences, coordinates, strict=True
            )
        ]
