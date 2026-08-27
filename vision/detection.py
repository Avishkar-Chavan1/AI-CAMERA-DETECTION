"""PPE-model adapter with an explicit class-label contract."""

from collections.abc import Mapping
from typing import Any, Protocol

from vision.errors import VisionModelError
from vision.models import BoundingBox, PpeDetection, PpeType


class PpeDetector(Protocol):
    """A detector that produces canonical PPE detections for one video frame."""

    enabled: bool

    def detect(self, frame: Any) -> list[PpeDetection]: ...


class UltralyticsPpeDetector:
    """Run a configured PPE-trained Ultralytics detection model."""

    enabled = True

    def __init__(
        self,
        model_reference: str,
        label_mapping: Mapping[str, str],
        confidence: float,
        iou_threshold: float,
    ) -> None:
        self._model = self._load_model(model_reference)
        self._label_mapping = {
            model_label.casefold(): PpeType(canonical_class)
            for model_label, canonical_class in label_mapping.items()
        }
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
        except Exception as error:  # Ultralytics exposes several runtime exception types
            raise VisionModelError(f"Unable to load PPE model: {model_reference!r}") from error

    def detect(self, frame: Any) -> list[PpeDetection]:
        """Return only model labels explicitly mapped to required PPE categories."""
        try:
            result = self._model.predict(
                source=frame,
                conf=self._confidence,
                iou=self._iou_threshold,
                verbose=False,
            )[0]
        except Exception as error:  # pragma: no cover - depends on model runtime and hardware
            raise VisionModelError("PPE model inference failed") from error

        boxes = result.boxes
        if boxes is None:
            return []

        detections: list[PpeDetection] = []
        classes = boxes.cls.int().cpu().tolist()
        confidences = boxes.conf.cpu().tolist()
        coordinates = boxes.xyxy.cpu().tolist()
        for class_id, confidence, xyxy in zip(classes, confidences, coordinates, strict=True):
            class_name = self._class_name(result.names, class_id)
            ppe_type = self._label_mapping.get(class_name.casefold())
            if ppe_type is None:
                continue
            detections.append(
                PpeDetection(
                    ppe_type=ppe_type,
                    bounding_box=BoundingBox(*map(float, xyxy)),
                    confidence=float(confidence),
                )
            )
        return detections

    @staticmethod
    def _class_name(names: Any, class_id: int) -> str:
        if isinstance(names, Mapping):
            return str(names[class_id])
        return str(names[class_id])
