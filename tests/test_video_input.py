import argparse
from pathlib import Path

import pytest
from vision.errors import VideoInputError
from vision.inference import run_inference
from vision.video_input import parse_video_source


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PPE YOLO inference on a local image or video.")
    parser.add_argument("source", type=Path, help="Path to an image or video file")
    parser.add_argument(
        "--model",
        type=Path,
        default=PROJECT_ROOT / "best.pt",
        help="Path to YOLO weights (default: project root best.pt)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "runs" / "inference",
        help="Directory for annotated output (default: runs/inference)",
    )
    parser.add_argument("--conf", type=float, default=0.25, help="Detection confidence threshold")
    parser.add_argument("--iou", type=float, default=0.45, help="NMS IoU threshold")
    args = parser.parse_args()

    try:
        result = run_inference(
            args.model.resolve(),
            args.source.resolve(),
            args.output.resolve(),
            args.conf,
            args.iou,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    print(f"Source: {result.source}")
    for detection in result.detections:
        print(f"Detected: {detection.class_name} confidence={detection.confidence:.4f}")
    print(f"Detection count: {len(result.detections)}")
    print(f"Annotated results saved to: {result.output_dir}")


if __name__ == "__main__":
    main()


def test_parse_video_source_converts_webcam_index() -> None:
    assert parse_video_source(" 0 ") == 0


def test_parse_video_source_keeps_local_file_path() -> None:
    assert parse_video_source("data/example.mp4") == "data/example.mp4"


def test_parse_video_source_rejects_blank_value() -> None:
    with pytest.raises(VideoInputError, match="VISION_SOURCE"):
        parse_video_source("   ")
