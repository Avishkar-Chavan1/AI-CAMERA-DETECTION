from pathlib import Path

import pytest

from vision.inference import DetectionRecord, _collect_detections, run_inference
from vision.models import BoundingBox


class FakeTensor:
    def __init__(self, values: list[float]) -> None:
        self.values = values

    def int(self) -> "FakeTensor":
        return self

    def cpu(self) -> "FakeTensor":
        return self

    def tolist(self) -> list[float]:
        return self.values


class FakeBoxes:
    cls = FakeTensor([0, 1])
    conf = FakeTensor([0.91, 0.42])
    xyxy = FakeTensor([[0, 0, 10, 10], [1, 1, 9, 9]])


class FakeResult:
    boxes = FakeBoxes()
    names = {0: "helmet", 1: "no_helmet"}


def test_collect_detections_returns_classes_and_confidence() -> None:
    assert _collect_detections([FakeResult()]) == [
        DetectionRecord("helmet", 0.91, BoundingBox(0, 0, 10, 10)),
        DetectionRecord("no_helmet", 0.42, BoundingBox(1, 1, 9, 9)),
    ]


def test_run_inference_rejects_missing_source(tmp_path: Path) -> None:
    model_path = tmp_path / "best.pt"
    model_path.write_bytes(b"placeholder")
    with pytest.raises(FileNotFoundError, match="Image or video file not found"):
        run_inference(model_path, tmp_path / "missing.mp4", tmp_path / "output")


def test_engine_rejects_missing_model(tmp_path: Path) -> None:
    from vision.inference import PpeInferenceEngine

    with pytest.raises(FileNotFoundError, match="Model file not found"):
        PpeInferenceEngine(tmp_path / "missing.pt")
