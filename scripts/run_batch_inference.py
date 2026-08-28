"""Run local YOLO inference over all configured real-world inputs."""

import argparse
import csv
from pathlib import Path

from vision.inference import InferenceResult, run_inference

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=PROJECT_ROOT / "best.pt")
    parser.add_argument("--images", type=Path, default=PROJECT_ROOT / "test_inputs" / "images")
    parser.add_argument("--videos", type=Path, default=PROJECT_ROOT / "test_inputs" / "videos")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "runs" / "inference")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    args = parser.parse_args()

    sources = [
        *sorted(path for path in args.images.glob("*") if path.suffix.casefold() in IMAGE_EXTENSIONS),
        *sorted(path for path in args.videos.glob("*") if path.suffix.casefold() in VIDEO_EXTENSIONS),
    ]
    if not sources:
        print("No supported image or video files found in test_inputs/images or test_inputs/videos.")
        return

    args.output.resolve().mkdir(parents=True, exist_ok=True)
    records: list[InferenceResult] = []
    for source in sources:
        result = run_inference(
            args.model.resolve(), source.resolve(), args.output.resolve(), args.conf, args.iou
        )
        records.append(result)
        print(f"{source.name}: {len(result.detections)} detections")
        for detection in result.detections:
            print(f"  {detection.class_name} confidence={detection.confidence:.4f}")

    summary_path = args.output.resolve() / "prediction_summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as summary_file:
        writer = csv.writer(summary_file)
        writer.writerow(["filename", "detected_class", "confidence", "detection_count"])
        for result in records:
            for detection in result.detections:
                writer.writerow(
                    [result.source.name, detection.class_name, f"{detection.confidence:.4f}", len(result.detections)]
                )
            if not result.detections:
                writer.writerow([result.source.name, "none", "", 0])
    print(f"Prediction summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
