"""Business rules for per-worker PPE compliance."""

from dataclasses import dataclass
from typing import Iterable

from vision.models import BoundingBox

REQUIRED_PPE_TYPES = ("helmet", "vest")
MISSING_LABELS = {
    "no_helmet": "helmet",
    "no_gloves": "gloves",
    "no_vest": "vest",
    "no_boots": "boots",
    "no_goggle": "goggles",
    "no_goggles": "goggles",
}


@dataclass(frozen=True)
class ComplianceDetection:
    class_name: str
    confidence: float
    bounding_box: BoundingBox | None = None


@dataclass(frozen=True)
class WorkerCompliance:
    worker_id: int
    status: str
    missing_ppe: tuple[str, ...]
    uncertain_ppe: tuple[str, ...]
    detections: tuple[ComplianceDetection, ...]


@dataclass(frozen=True)
class ComplianceSummary:
    total_people: int
    safe_workers: int
    workers_with_violations: int
    total_violations: int
    violation_types: tuple[str, ...]


def analyze_compliance(
    detections: Iterable[ComplianceDetection],
    person_boxes: Iterable[tuple[int, BoundingBox]],
    min_confidence: float = 0.25,
) -> tuple[tuple[WorkerCompliance, ...], ComplianceSummary]:
    """Determine compliance from explicit violation and required PPE evidence."""
    all_detections = tuple(item for item in detections if item.confidence >= min_confidence)
    workers: list[WorkerCompliance] = []
    violation_types: set[str] = set()
    total_violations = 0
    for worker_id, person_box in person_boxes:
        related = tuple(
            detection for detection in all_detections
            if detection.bounding_box is not None
            and person_box.containment_ratio(detection.bounding_box) >= 0.05
        )
        missing: list[str] = []
        uncertain: list[str] = []
        explicit_missing = {
            MISSING_LABELS[item.class_name.casefold()]
            for item in related
            if item.class_name.casefold() in MISSING_LABELS
        }
        missing.extend(sorted(explicit_missing))
        violation_types.update(explicit_missing)
        for ppe_type in REQUIRED_PPE_TYPES:
            if ppe_type in explicit_missing:
                continue
            if not any(item.class_name.casefold() == ppe_type for item in related):
                uncertain.append(ppe_type)
        if missing:
            status = "VIOLATION"
            total_violations += len(missing)
        elif uncertain:
            status = "UNKNOWN"
        else:
            status = "SAFE"
        workers.append(WorkerCompliance(worker_id, status, tuple(missing), tuple(uncertain), related))
    safe = sum(worker.status == "SAFE" for worker in workers)
    violations = sum(worker.status == "VIOLATION" for worker in workers)
    summary = ComplianceSummary(len(workers), safe, violations, total_violations, tuple(sorted(violation_types)))
    return tuple(workers), summary
