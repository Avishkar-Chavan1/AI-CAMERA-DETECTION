from vision.association import AssociationPolicy, PpeAssociator
from vision.models import BoundingBox, PpeDetection, PpeType, TrackedWorker


def worker(worker_id: int, left: float) -> TrackedWorker:
    return TrackedWorker(
        worker_id=worker_id,
        bounding_box=BoundingBox(left, 0, left + 100, 200),
        confidence=0.90,
    )


def ppe(
    ppe_type: PpeType,
    left: float,
    top: float,
    right: float,
    bottom: float,
    confidence: float = 0.80,
) -> PpeDetection:
    return PpeDetection(
        ppe_type=ppe_type,
        bounding_box=BoundingBox(left, top, right, bottom),
        confidence=confidence,
    )


def test_associate_attaches_ppe_to_the_spatially_matching_worker() -> None:
    associator = PpeAssociator(AssociationPolicy(min_containment=0.20))
    workers = [worker(1, 0), worker(2, 120)]
    detections = [
        ppe(PpeType.HELMET, 20, 10, 65, 45, 0.92),
        ppe(PpeType.VEST, 25, 65, 75, 150, 0.88),
        ppe(PpeType.SHOES, 25, 155, 75, 195, 0.81),
    ]

    statuses = associator.associate(workers, detections, ppe_model_enabled=True)

    assert statuses[0].worker_id == 1
    assert statuses[0].helmet_present is True
    assert statuses[0].helmet_confidence == 0.92
    assert statuses[0].vest_present is True
    assert statuses[0].shoes_present is True
    assert statuses[1].worker_id == 2
    assert statuses[1].helmet_present is False
    assert statuses[1].vest_present is False
    assert statuses[1].shoes_present is False


def test_associate_reports_unknown_status_when_no_ppe_model_is_configured() -> None:
    associator = PpeAssociator(AssociationPolicy(min_containment=0.20))

    status = associator.associate([worker(1, 0)], [], ppe_model_enabled=False)[0]

    assert status.helmet_present is None
    assert status.helmet_confidence is None
    assert status.vest_present is None
    assert status.shoes_present is None


def test_associate_rejects_detection_in_an_incompatible_body_region() -> None:
    associator = PpeAssociator(AssociationPolicy(min_containment=0.20))
    high_helmet = ppe(PpeType.HELMET, 20, 130, 65, 185)

    status = associator.associate([worker(1, 0)], [high_helmet], ppe_model_enabled=True)[0]

    assert status.helmet_present is False
