"""OpenCV rendering for tracked workers and PPE observations."""

from typing import Any

from vision.models import PpeDetection, PpeType, WorkerPpeStatus

WORKER_COLOR = (0, 255, 0)
UNKNOWN_COLOR = (0, 215, 255)
MISSING_COLOR = (0, 0, 255)
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

    visible_workers = sorted(workers, key=lambda worker: worker.bounding_box.left)
    for display_id, worker in enumerate(visible_workers, start=1):
        box = worker.bounding_box
        cv2.rectangle(
            canvas,
            (int(box.left), int(box.top)),
            (int(box.right), int(box.bottom)),
            WORKER_COLOR,
            2,
        )
        _draw_worker_panel(canvas, worker, display_id)
    return canvas


def _draw_worker_panel(frame: Any, worker: WorkerPpeStatus, display_id: int) -> None:
    """Draw one aligned worker header and PPE status block."""
    import cv2

    rows = [
        ("Helmet", worker.helmet_present, worker.helmet_confidence),
        ("Vest", worker.vest_present, worker.vest_confidence),
        ("Shoes", worker.shoes_present, worker.shoes_confidence),
    ]
    row_height = 17
    panel_height = row_height * (len(rows) + 1) + 8
    panel_width = 146
    x = max(0, int(worker.bounding_box.left))
    y = int(worker.bounding_box.top) - panel_height - 4
    if y < 0:
        y = int(worker.bounding_box.top) + 4

    cv2.rectangle(
        frame,
        (x, y),
        (x + panel_width, y + panel_height),
        (20, 20, 20),
        cv2.FILLED,
    )
    cv2.rectangle(frame, (x, y), (x + panel_width, y + panel_height), WORKER_COLOR, 1)
    cv2.putText(
        frame,
        f"Worker #{display_id}  {worker.tracking_confidence:.2f}",
        (x + 4, y + 15),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        WORKER_COLOR,
        1,
        cv2.LINE_AA,
    )
    for row_index, (name, present, confidence) in enumerate(rows, start=1):
        color = _status_color(present)
        cv2.putText(
            frame,
            status_line(name, present, confidence),
            (x + 4, y + 15 + row_index * row_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.40,
            color,
            1,
            cv2.LINE_AA,
        )


def _status_color(present: bool | None) -> tuple[int, int, int]:
    """Return a readable BGR color for a PPE state."""
    if present is True:
        return WORKER_COLOR
    if present is False:
        return MISSING_COLOR
    return UNKNOWN_COLOR


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
