"""Local YOLO image and video inference helpers."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vision.compliance import ComplianceDetection
from vision.models import BoundingBox


@dataclass(frozen=True)
class DetectionRecord:
    """One detected class and confidence for an input source."""

    class_name: str
    confidence: float
    bounding_box: BoundingBox | None = None


@dataclass(frozen=True)
class InferenceResult:
    """Saved output and detections for one image or video source."""

    source: Path
    output_dir: Path
    detections: tuple[DetectionRecord, ...]


VIOLATION_CLASSES = frozenset({"no_helmet", "no_gloves", "no_boots", "no_goggle", "none"})


class PpeInferenceEngine:
    """Reusable YOLO inference service for UI, API, image, and video callers."""

    def __init__(self, model_path: Path, confidence: float = 0.25, iou: float = 0.45) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        if not 0.0 < confidence <= 1.0 or not 0.0 < iou <= 1.0:
            raise ValueError("confidence and iou must be greater than 0 and at most 1")
        try:
            from ultralytics import YOLO

            self._model = YOLO(str(model_path))
        except ImportError as error:
            raise RuntimeError("Ultralytics is unavailable in the active environment") from error
        except Exception as error:
            raise RuntimeError(f"Unable to load model: {model_path}") from error
        self.confidence = confidence
        self.iou = iou

    def predict_frame(
        self,
        frame: Any,
        confidence: float | None = None,
        iou: float | None = None,
    ) -> tuple[Any, tuple[DetectionRecord, ...], str]:
        """Predict one BGR frame and return an annotated frame, detections, and status."""
        try:
            result = self._model.predict(
                source=frame,
                conf=self.confidence if confidence is None else confidence,
                iou=self.iou if iou is None else iou,
                verbose=False,
            )[0]
        except Exception as error:
            raise RuntimeError("PPE frame inference failed") from error
        detections = tuple(_collect_detections([result]))
        annotated = result.plot()
        status = "VIOLATION DETECTED" if any(
            detection.class_name.casefold() in VIOLATION_CLASSES for detection in detections
        ) else "SAFE"
        return annotated, detections, status


def run_inference(
    model_path: Path,
    source_path: Path,
    output_dir: Path,
    confidence: float = 0.25,
    iou: float = 0.45,
) -> InferenceResult:
    """Run YOLO inference on one local image or video and save annotations."""
    if "<" in str(source_path) or ">" in str(source_path):
        raise FileNotFoundError(
            "Replace the placeholder filename with a real file in test_inputs/images or videos."
        )
    if not model_path.is_file():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not source_path.is_file():
        raise FileNotFoundError(f"Image or video file not found: {source_path}")
    if not 0.0 < confidence <= 1.0:
        raise ValueError("confidence must be greater than 0 and at most 1")
    if not 0.0 < iou <= 1.0:
        raise ValueError("iou must be greater than 0 and at most 1")

    try:
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError(
            "Ultralytics is unavailable. Install the vision dependencies in the project environment."
        ) from error

    try:
        model = YOLO(str(model_path))
        results = model.predict(
            source=str(source_path),
            conf=confidence,
            iou=iou,
            save=True,
            project=str(output_dir.parent),
            name=output_dir.name,
            exist_ok=True,
            verbose=False,
        )
        detections = tuple(_collect_detections(results))
    except Exception as error:
        raise RuntimeError(f"Inference failed for {source_path}") from error

    return InferenceResult(source_path, output_dir, detections)


def _collect_detections(results: Any) -> list[DetectionRecord]:
    detections: list[DetectionRecord] = []
    for result in results:
        if result.boxes is None:
            continue
        class_ids = result.boxes.cls.int().cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        coordinates = result.boxes.xyxy.cpu().tolist()
        for class_id, score, coordinates_for_detection in zip(
            class_ids, confidences, coordinates, strict=True
        ):
            detections.append(
                DetectionRecord(
                    str(result.names[class_id]),
                    float(score),
                    BoundingBox(*map(float, coordinates_for_detection)),
                )
            )
    return detections
