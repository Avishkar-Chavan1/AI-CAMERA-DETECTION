"""Exception types exposed by the vision runtime."""


class VisionError(RuntimeError):
    """Base class for expected vision-runtime failures."""


class VisionConfigurationError(VisionError):
    """Raised when the configured vision runtime cannot be constructed."""


class VisionModelError(VisionError):
    """Raised when a configured detection or tracking model cannot be used."""


class VideoInputError(VisionError):
    """Raised when a camera or local video source cannot be opened."""
