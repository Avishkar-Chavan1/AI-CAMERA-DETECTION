"""OpenCV rendering for tracked workers and PPE observations."""

from typing import Any

from vision.models import PpeDetection, PpeType, WorkerPpeStatus


WORKER_COLOR = (0, 255, 0)
PPE_COLORS = {
    PpeType.HELMET: (0, 255, 255),
    PpeType.VEST: (255, 128, 0),
    PpeType.SHOES: (255, 0, 255),
}


def status_line(name: str, present: bool | None, confidence: float | None) -> str:
    """Format a concise, font-safe PPE label for an OpenCV image."""
    if present is None:
        return f"{name}: ?"
    if present:
        suffix = f" {confidence:.2f}" if confidence is not None else ""
        return f"{name}: YES{suffix}"
    return f"{name}: NO"


def annotate_frame(
    frame: Any,
    workers: list[WorkerPpeStatus],
    ppe_detections: list[PpeDetection],
) -> Any:
    """Return a copy of a frame annotated with worker and PPE information."""
    try:
        import cv2
    except ImportError as error:  # pragma: no cover - guarded by the vision extra
        message = "OpenCV is unavailable. Install the project with the 'vision' extra."
        raise RuntimeError(message) from error

    canvas = frame.copy()
    for detection in ppe_detections:
        box = detection.bounding_box
        color = PPE_COLORS[detection.ppe_type]
        cv2.rectangle(
            canvas,
            (int(box.left), int(box.top)),
            (int(box.right), int(box.bottom)),
            color,
            2,
        )
        _draw_label(
            canvas,
            f"{detection.ppe_type.value} {detection.confidence:.2f}",
            int(box.left),
            int(box.top) - 6,
            color,
        )

    for worker in workers:
        box = worker.bounding_box
        cv2.rectangle(
            canvas,
            (int(box.left), int(box.top)),
            (int(box.right), int(box.bottom)),
            WORKER_COLOR,
            2,
        )
        lines = [
            f"Worker #{worker.worker_id} {worker.tracking_confidence:.2f}",
            status_line("Helmet", worker.helmet_present, worker.helmet_confidence),
            status_line("Vest", worker.vest_present, worker.vest_confidence),
            status_line("Shoes", worker.shoes_present, worker.shoes_confidence),
        ]
        label_y = max(16, int(box.top) - len(lines) * 18)
        for line in lines:
            _draw_label(canvas, line, int(box.left), label_y, WORKER_COLOR)
            label_y += 18
    return canvas


def _draw_label(frame: Any, text: str, x: int, y: int, color: tuple[int, int, int]) -> None:
    """Draw a label with a solid background so it remains legible over video."""
    import cv2

    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.48
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
    top_left = (x, max(0, y - text_height - baseline - 4))
    bottom_right = (x + text_width + 4, y + 3)
    cv2.rectangle(frame, top_left, bottom_right, (0, 0, 0), cv2.FILLED)
    cv2.putText(frame, text, (x + 2, y), font, scale, color, thickness, cv2.LINE_AA)
