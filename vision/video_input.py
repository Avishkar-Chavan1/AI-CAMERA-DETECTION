"""OpenCV-backed input for webcams and local video files."""

from collections.abc import Callable, Iterator
from typing import Any, Protocol

from vision.errors import VideoInputError


class Capture(Protocol):
    """Minimal OpenCV capture surface used by the input adapter."""

    def isOpened(self) -> bool: ...

    def read(self) -> tuple[bool, Any]: ...

    def release(self) -> None: ...


CaptureFactory = Callable[[int | str], Capture]


def parse_video_source(source: str) -> int | str:
    """Convert a non-negative numeric source into a webcam index, otherwise keep its path."""
    normalized = source.strip()
    if not normalized:
        raise VideoInputError("VISION_SOURCE must be a webcam index or a local video-file path")
    if normalized.isdecimal():
        return int(normalized)
    return normalized


class OpenCvVideoInput:
    """Read frames from exactly one configured webcam or local video file."""

    def __init__(self, source: str, capture_factory: CaptureFactory | None = None) -> None:
        self.source = parse_video_source(source)
        self._capture_factory = capture_factory or self._create_capture
        self._capture: Capture | None = None

    @staticmethod
    def _create_capture(source: int | str) -> Capture:
        try:
            import cv2
        except ImportError as error:  # pragma: no cover - guarded by the vision extra
            message = "OpenCV is unavailable. Install the project with the 'vision' extra."
            raise VideoInputError(message) from error
        return cv2.VideoCapture(source)

    def open(self) -> None:
        """Open the configured input source once."""
        if self._capture is not None:
            return
        capture = self._capture_factory(self.source)
        if not capture.isOpened():
            capture.release()
            raise VideoInputError(f"Unable to open video input: {self.source!r}")
        self._capture = capture

    def frames(self) -> Iterator[Any]:
        """Yield frames until the webcam disconnects or the local file ends."""
        if self._capture is None:
            self.open()
        if self._capture is None:  # pragma: no cover - defensive guard for type narrowing
            raise VideoInputError("Video input failed to initialize")

        while True:
            success, frame = self._capture.read()
            if not success:
                return
            yield frame

    def close(self) -> None:
        """Release the camera or file handle if it was opened."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self) -> "OpenCvVideoInput":
        self.open()
        return self

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()
