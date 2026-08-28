"""API-facing adapters for model inference and compliance results."""

from vision.compliance import ComplianceDetection, analyze_compliance
from vision.inference import DetectionRecord, PpeInferenceEngine


def frame_response(
    engine: PpeInferenceEngine,
    frame: object,
    confidence: float | None = None,
    iou: float | None = None,
) -> dict[str, object]:
    """Return JSON-safe detections and per-worker compliance for one frame."""
    _, detections, _ = engine.predict_frame(frame, confidence, iou)
    people = [
        (index, detection.bounding_box)
        for index, detection in enumerate(detections, start=1)
        if detection.class_name.casefold() == "person" and detection.bounding_box is not None
    ]
    observations = [
        ComplianceDetection(item.class_name, item.confidence, item.bounding_box)
        for item in detections
    ]
    workers, summary = analyze_compliance(
        observations,
        people,
        engine.confidence if confidence is None else confidence,
    )
    if summary.workers_with_violations:
        overall_status = "VIOLATION"
    elif not summary.total_people or summary.safe_workers != summary.total_people:
        overall_status = "UNKNOWN"
    else:
        overall_status = "SAFE"
    return {
        "detections": [_detection_payload(detection) for detection in detections],
        "workers": [
            {
                "worker_id": worker.worker_id,
                "status": worker.status,
                "violations": list(worker.missing_ppe),
                "uncertain_ppe": list(worker.uncertain_ppe),
            }
            for worker in workers
        ],
        "summary": {
            "status": overall_status,
            "total_people": summary.total_people,
            "safe_workers": summary.safe_workers,
            "workers_with_violations": summary.workers_with_violations,
            "total_violations": summary.total_violations,
            "violation_types": list(summary.violation_types),
        },
    }


def _detection_payload(detection: DetectionRecord) -> dict[str, object]:
    box = detection.bounding_box
    class_name = detection.class_name.casefold()
    if class_name.startswith("no_") or class_name in {"none", "unknown"}:
        compliance_status = "violation"
    elif class_name in {"helmet", "gloves", "vest", "boots", "shoes", "goggles"}:
        compliance_status = "compliant"
    else:
        compliance_status = "unknown"
    return {
        "class": detection.class_name,
        "class_name": detection.class_name,
        "confidence": detection.confidence,
        "compliance_status": compliance_status,
        "bounding_box": None if box is None else {
            "left": box.left, "top": box.top, "right": box.right, "bottom": box.bottom
        },
    }
