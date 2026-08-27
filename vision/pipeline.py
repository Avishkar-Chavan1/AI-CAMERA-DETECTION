"""Composition root for the Phase 2 local video-processing runtime."""

from dataclasses import dataclass

from backend.app.core.config import Settings

from vision.association import AssociationPolicy, PpeAssociator
from vision.detection import PpeDetector, UltralyticsPpeDetector
from vision.errors import VisionConfigurationError
from vision.tracking import UltralyticsPersonTracker
from vision.video_input import OpenCvVideoInput
from vision.visualization import annotate_frame


@dataclass(frozen=True)
class VisionRunSummary:
    """A factual summary of one local video-processing run."""

    frames_processed: int
    stopped_by_user: bool


class VisionPipeline:
    """Process one webcam or local video source through tracking and PPE association."""

    def __init__(
        self,
        video_input: OpenCvVideoInput,
        person_tracker: UltralyticsPersonTracker,
        ppe_detector: PpeDetector | None,
        ppe_associator: PpeAssociator,
        display: bool,
        window_name: str,
    ) -> None:
        self._video_input = video_input
        self._person_tracker = person_tracker
        self._ppe_detector = ppe_detector
        self._ppe_associator = ppe_associator
        self._display = display
        self._window_name = window_name

    @classmethod
    def from_settings(cls, settings: Settings) -> "VisionPipeline":
        """Construct the pipeline only from validated application settings."""
        if settings.vision_source is None:
            raise VisionConfigurationError(
                "VISION_SOURCE is required. Set it to a webcam index or a local video-file path."
            )

        ppe_detector: PpeDetector | None = None
        if settings.vision_ppe_model is not None:
            if settings.vision_ppe_class_map is None:  # validated by Settings; retained defensively
                raise VisionConfigurationError("VISION_PPE_CLASS_MAP is required for PPE detection")
            ppe_detector = UltralyticsPpeDetector(
                model_reference=settings.vision_ppe_model,
                label_mapping=settings.vision_ppe_class_map,
                confidence=settings.vision_ppe_min_confidence,
                iou_threshold=settings.vision_iou_threshold,
            )

        return cls(
            video_input=OpenCvVideoInput(settings.vision_source),
            person_tracker=UltralyticsPersonTracker(
                model_reference=settings.vision_person_model,
                tracker_configuration=settings.vision_tracker,
                confidence=settings.vision_confidence,
                iou_threshold=settings.vision_iou_threshold,
            ),
            ppe_detector=ppe_detector,
            ppe_associator=PpeAssociator(
                AssociationPolicy(min_containment=settings.vision_association_min_containment)
            ),
            display=settings.vision_display,
            window_name=settings.vision_window_name,
        )

    def run(self) -> VisionRunSummary:
        """Process frames until a file ends, a camera stops, or the user presses Q/Esc."""
        frames_processed = 0
        stopped_by_user = False
        self._video_input.open()
        try:
            for frame in self._video_input.frames():
                workers = self._person_tracker.track(frame)
                ppe_detections = self._ppe_detector.detect(frame) if self._ppe_detector else []
                worker_statuses = self._ppe_associator.associate(
                    workers=workers,
                    ppe_detections=ppe_detections,
                    ppe_model_enabled=self._ppe_detector is not None,
                )
                frames_processed += 1

                if self._display:
                    if self._show(annotate_frame(frame, worker_statuses, ppe_detections)):
                        stopped_by_user = True
                        break
        finally:
            self._video_input.close()
            if self._display:
                self._close_window()
        return VisionRunSummary(frames_processed=frames_processed, stopped_by_user=stopped_by_user)

    def _show(self, frame: object) -> bool:
        import cv2

        cv2.imshow(self._window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        return key in {27, ord("q"), ord("Q")}

    def _close_window(self) -> None:
        import cv2

        cv2.destroyAllWindows()
