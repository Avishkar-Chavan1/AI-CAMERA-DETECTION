from vision.compliance import ComplianceDetection, analyze_compliance
from vision.models import BoundingBox


def test_worker_with_complete_ppe_is_safe() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [
        ComplianceDetection(name, 0.9, BoundingBox(10, 10 + index * 15, 30, 25 + index * 15))
        for index, name in enumerate(("helmet", "gloves", "vest", "boots", "goggles"))
    ]
    workers, summary = analyze_compliance(detections, [(7, person)])
    assert workers[0].status == "SAFE"
    assert summary.safe_workers == 1


def test_missing_ppe_is_a_violation_with_type() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [ComplianceDetection("no_gloves", 0.82, BoundingBox(10, 40, 30, 60))]
    workers, summary = analyze_compliance(detections, [(3, person)])
    assert workers[0].status == "VIOLATION"
    assert workers[0].missing_ppe == ("gloves",)
    assert summary.total_violations == 1


def test_missing_evidence_is_unknown_not_safe() -> None:
    person = BoundingBox(0, 0, 100, 100)
    workers, summary = analyze_compliance([], [(1, person)])
    assert workers[0].status == "UNKNOWN"
    assert summary.safe_workers == 0


def test_person_with_required_helmet_and_vest_is_safe() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [
        ComplianceDetection("helmet", 0.9, BoundingBox(10, 5, 35, 25)),
        ComplianceDetection("vest", 0.9, BoundingBox(20, 30, 80, 85)),
    ]

    workers, summary = analyze_compliance(detections, [(1, person)])

    assert workers[0].status == "SAFE"
    assert workers[0].uncertain_ppe == ()
    assert summary.safe_workers == 1


def test_person_with_explicit_missing_helmet_is_violation() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [ComplianceDetection("no_helmet", 0.9, BoundingBox(10, 5, 35, 25))]

    workers, summary = analyze_compliance(detections, [(1, person)])

    assert workers[0].status == "VIOLATION"
    assert workers[0].missing_ppe == ("helmet",)
    assert summary.total_violations == 1


def test_person_without_explicit_vest_label_remains_unknown() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [ComplianceDetection("helmet", 0.9, BoundingBox(10, 5, 35, 25))]

    workers, summary = analyze_compliance(detections, [(1, person)])

    assert workers[0].status == "UNKNOWN"
    assert workers[0].uncertain_ppe == ("vest",)
    assert summary.workers_with_violations == 0


def test_explicit_missing_helmet_and_vest_are_both_violations() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [
        ComplianceDetection("no_helmet", 0.9, BoundingBox(10, 5, 35, 25)),
        ComplianceDetection("no_vest", 0.9, BoundingBox(20, 30, 80, 85)),
    ]

    workers, summary = analyze_compliance(detections, [(1, person)])

    assert workers[0].status == "VIOLATION"
    assert workers[0].missing_ppe == ("helmet", "vest")
    assert summary.total_violations == 2


def test_mixed_workers_keep_individual_compliance_status() -> None:
    detections = [
        ComplianceDetection("helmet", 0.9, BoundingBox(10, 5, 35, 25)),
        ComplianceDetection("vest", 0.9, BoundingBox(20, 30, 80, 85)),
        ComplianceDetection("no_helmet", 0.9, BoundingBox(130, 5, 155, 25)),
        ComplianceDetection("vest", 0.9, BoundingBox(140, 30, 180, 85)),
    ]
    people = [(1, BoundingBox(0, 0, 100, 100)), (2, BoundingBox(120, 0, 220, 100))]

    workers, summary = analyze_compliance(detections, people)

    assert [worker.status for worker in workers] == ["SAFE", "VIOLATION"]
    assert summary.safe_workers == 1
    assert summary.workers_with_violations == 1


def test_low_confidence_missing_label_is_not_a_violation() -> None:
    person = BoundingBox(0, 0, 100, 100)
    detections = [
        ComplianceDetection("helmet", 0.9, BoundingBox(10, 5, 35, 25)),
        ComplianceDetection("vest", 0.9, BoundingBox(20, 30, 80, 85)),
        ComplianceDetection("no_helmet", 0.1, BoundingBox(10, 5, 35, 25)),
    ]

    workers, summary = analyze_compliance(detections, [(1, person)], min_confidence=0.25)

    assert workers[0].status == "SAFE"
    assert summary.total_violations == 0
