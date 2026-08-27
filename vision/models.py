"""Vision-domain value objects shared across the processing pipeline."""

from dataclasses import dataclass
from enum import StrEnum


class PpeType(StrEnum):
    """Canonical PPE categories supported by the Phase 2 UI."""

    HELMET = "helmet"
    VEST = "vest"
    SHOES = "shoes"


@dataclass(frozen=True)
class BoundingBox:
    """A normalized, image-coordinate bounding box in left-top-right-bottom form."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("BoundingBox requires right > left and bottom > top")

    @property
    def width(self) -> float:
        """Return the box width in image pixels."""
        return self.right - self.left

    @property
    def height(self) -> float:
        """Return the box height in image pixels."""
        return self.bottom - self.top

    @property
    def area(self) -> float:
        """Return the box area in square pixels."""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """Return the box centre in image pixels."""
        return (self.left + self.width / 2, self.top + self.height / 2)

    def containment_ratio(self, candidate: "BoundingBox") -> float:
        """Return the fraction of a candidate box that lies inside this box."""
        intersection_left = max(self.left, candidate.left)
        intersection_top = max(self.top, candidate.top)
        intersection_right = min(self.right, candidate.right)
        intersection_bottom = min(self.bottom, candidate.bottom)
        intersection_width = max(0.0, intersection_right - intersection_left)
        intersection_height = max(0.0, intersection_bottom - intersection_top)
        return (intersection_width * intersection_height) / candidate.area


@dataclass(frozen=True)
class TrackedWorker:
    """A person detection that has received a persistent tracker identifier."""

    worker_id: int
    bounding_box: BoundingBox
    confidence: float


@dataclass(frozen=True)
class PpeDetection:
    """A PPE detection from a configured PPE-specific model."""

    ppe_type: PpeType
    bounding_box: BoundingBox
    confidence: float


@dataclass(frozen=True)
class WorkerPpeStatus:
    """PPE state associated with a tracked worker for one processed frame."""

    worker_id: int
    bounding_box: BoundingBox
    tracking_confidence: float
    helmet_present: bool | None
    helmet_confidence: float | None
    vest_present: bool | None
    vest_confidence: float | None
    shoes_present: bool | None
    shoes_confidence: float | None
