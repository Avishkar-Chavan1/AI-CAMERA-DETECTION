import pytest
from vision.errors import VideoInputError
from vision.video_input import parse_video_source


def test_parse_video_source_converts_webcam_index() -> None:
    assert parse_video_source(" 0 ") == 0


def test_parse_video_source_keeps_local_file_path() -> None:
    assert parse_video_source("data/example.mp4") == "data/example.mp4"


def test_parse_video_source_rejects_blank_value() -> None:
    with pytest.raises(VideoInputError, match="VISION_SOURCE"):
        parse_video_source("   ")
