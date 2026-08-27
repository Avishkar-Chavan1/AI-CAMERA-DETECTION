"""Spatial association between tracked workers and PPE detections."""

from dataclasses import dataclass

from vision.models import PpeDetection, PpeType, TrackedWorker, WorkerPpeStatus


PPE_VERTICAL_BANDS: dict[PpeType, tuple[float, float]] = {
    PpeType.HELMET: (0.0, 0.45),
    PpeType.VEST: (0.15, 0.90),
    PpeType.SHOES: (0.60, 1.10),
}


@dataclass(frozen=True)
class AssociationPolicy:
    """Tunable minimum geometry required to associate PPE to a worker."""

    min_containment: float


class PpeAssociator:
    """Attach each PPE detection to at most one spatially compatible worker."""

    def __init__(self, policy: AssociationPolicy) -> None:
        self._policy = policy

    def associate(
        self,
        workers: list[TrackedWorker],
        ppe_detections: list[PpeDetection],
        ppe_model_enabled: bool,
    ) -> list[WorkerPpeStatus]:
        """Return PPE state per worker without fabricating unavailable-model results."""
        assigned: dict[int, dict[PpeType, PpeDetection]] = {
            worker.worker_id: {} for worker in workers
        }

        if ppe_model_enabled:
            for detection in ppe_detections:
                candidate = self._best_worker_for_detection(detection, workers)
                if candidate is None:
                    continue
                existing = assigned[candidate.worker_id].get(detection.ppe_type)
                if existing is None or detection.confidence > existing.confidence:
                    assigned[candidate.worker_id][detection.ppe_type] = detection

        return [
            self._worker_status(worker, assigned[worker.worker_id], ppe_model_enabled)
            for worker in workers
        ]

    def _best_worker_for_detection(
        self,
        detection: PpeDetection,
        workers: list[TrackedWorker],
    ) -> TrackedWorker | None:
        candidates = [
            (self._association_score(worker, detection), worker)
            for worker in workers
        ]
        compatible = [(score, worker) for score, worker in candidates if score is not None]
        if not compatible:
            return None
        return max(compatible, key=lambda item: item[0])[1]

    def _association_score(self, worker: TrackedWorker, detection: PpeDetection) -> float | None:
        containment = worker.bounding_box.containment_ratio(detection.bounding_box)
        if containment < self._policy.min_containment:
            return None

        center_x, center_y = detection.bounding_box.center
        if not worker.bounding_box.left <= center_x <= worker.bounding_box.right:
            return None

        vertical_position = (center_y - worker.bounding_box.top) / worker.bounding_box.height
        lower_bound, upper_bound = PPE_VERTICAL_BANDS[detection.ppe_type]
        if not lower_bound <= vertical_position <= upper_bound:
            return None

        return detection.confidence * containment

    @staticmethod
    def _worker_status(
        worker: TrackedWorker,
        detections: dict[PpeType, PpeDetection],
        ppe_model_enabled: bool,
    ) -> WorkerPpeStatus:
        def status_for(ppe_type: PpeType) -> tuple[bool | None, float | None]:
            if not ppe_model_enabled:
                return None, None
            detection = detections.get(ppe_type)
            if detection is None:
                return False, None
            return True, detection.confidence

        helmet_present, helmet_confidence = status_for(PpeType.HELMET)
        vest_present, vest_confidence = status_for(PpeType.VEST)
        shoes_present, shoes_confidence = status_for(PpeType.SHOES)
        return WorkerPpeStatus(
            worker_id=worker.worker_id,
            bounding_box=worker.bounding_box,
            tracking_confidence=worker.confidence,
            helmet_present=helmet_present,
            helmet_confidence=helmet_confidence,
            vest_present=vest_present,
            vest_confidence=vest_confidence,
            shoes_present=shoes_present,
            shoes_confidence=shoes_confidence,
        )
