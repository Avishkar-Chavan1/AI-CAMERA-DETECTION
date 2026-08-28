"""Streamlit UI for local industrial PPE inference."""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from io import StringIO
import csv

import streamlit as st

from vision.inference import DetectionRecord, PpeInferenceEngine
from vision.compliance import ComplianceDetection, MISSING_LABELS, analyze_compliance
from vision.event_log import EventLogger

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = Path(os.getenv("MODEL_PATH", "best.pt"))
if not MODEL_PATH.is_absolute():
    MODEL_PATH = PROJECT_ROOT / MODEL_PATH
OUTPUT_DIR = PROJECT_ROOT / "runs" / "inference"
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY")
API_REQUEST_TIMEOUT_SECONDS = float(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "300"))


def compliance_for(detections: tuple[DetectionRecord, ...]):
    people = [
        (index, detection.bounding_box)
        for index, detection in enumerate(detections, start=1)
        if detection.class_name.casefold() == "person" and detection.bounding_box is not None
    ]
    observations = [
        ComplianceDetection(item.class_name, item.confidence, item.bounding_box)
        for item in detections
    ]
    return analyze_compliance(observations, people)


def show_detections(detections: tuple[DetectionRecord, ...]) -> None:
    workers, summary = compliance_for(detections)
    st.subheader("VIOLATION DETECTED" if summary.workers_with_violations else "SAFE")
    st.metric("Total people detected", summary.total_people)
    st.metric("Safe workers", summary.safe_workers)
    st.metric("Workers with violations", summary.workers_with_violations)
    st.metric("Total violations", summary.total_violations)
    st.write("Violation types:", ", ".join(summary.violation_types) or "None")
    for worker in workers:
        detail = ", ".join(worker.missing_ppe) or ", ".join(worker.uncertain_ppe)
        st.write(f"Worker {worker.worker_id}: {worker.status} ({detail or 'no PPE evidence'})")
    if not detections:
        st.write("No detections")
        return
    st.dataframe(
        [{"class": item.class_name, "confidence": round(item.confidence, 4)} for item in detections],
        use_container_width=True,
        hide_index=True,
    )


def show_api_response(response: dict[str, object]) -> None:
    summary = response.get("summary", {})
    if not isinstance(summary, dict):
        st.error("Backend returned an invalid inference response")
        return
    status = summary.get("status", "SAFE_OR_UNKNOWN")
    if status == "VIOLATION":
        st.error("VIOLATION DETECTED")
    elif status == "SAFE":
        st.success("SAFE / COMPLIANT")
    else:
        st.warning("UNKNOWN / INSUFFICIENT EVIDENCE")
    st.metric("Total people detected", summary.get("total_people", 0))
    st.metric("Workers with violations", summary.get("workers_with_violations", 0))
    st.metric("Total violations", summary.get("total_violations", 0))
    detections = response.get("detections", [])
    if isinstance(detections, list):
        st.dataframe(detections, use_container_width=True, hide_index=True)


def show_backend_status() -> None:
    import requests

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/health", timeout=5)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Backend returned invalid health data")
        if payload.get("model_loaded"):
            st.success("Backend online and model loaded")
        else:
            st.warning(f"Backend online but degraded: {payload.get('model_error', 'model unavailable')}")
    except (requests.RequestException, ValueError) as error:
        st.error(f"Backend unavailable: {error}")


def show_event_history() -> None:
    import requests

    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/events", params={"limit": 100}, timeout=5)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Backend returned invalid event data")
        events = payload.get("events", [])
        if events:
            st.dataframe(events, use_container_width=True, hide_index=True)
        else:
            st.info("No persisted inference events yet")
    except (requests.RequestException, ValueError) as error:
        st.warning(f"Event history unavailable: {error}")


def call_backend(path: str, uploaded_file: object, confidence: float, iou: float) -> dict[str, object]:
    import requests

    try:
        result = requests.post(
            f"{API_BASE_URL}{path}",
            params={"confidence": confidence, "iou": iou},
            headers={"X-API-Key": API_KEY} if API_KEY else {},
            files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
            timeout=API_REQUEST_TIMEOUT_SECONDS,
        )
        result.raise_for_status()
        payload = result.json()
    except requests.RequestException as error:
        raise RuntimeError(f"Backend request failed: {error}") from error
    except ValueError as error:
        raise RuntimeError("Backend returned invalid JSON") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Backend returned an invalid response")
    return payload


def process_image(uploaded_file: object, confidence: float, iou: float) -> None:
    st.image(uploaded_file, use_container_width=True)
    show_api_response(call_backend("/api/v1/inference/image", uploaded_file, confidence, iou))


def process_video(uploaded_file: object, confidence: float, iou: float) -> None:
    response = call_backend("/api/v1/inference/video", uploaded_file, confidence, iou)
    st.write(f"Processed {response.get('frame_count', 0)} frames")
    frames = response.get("frames", [])
    if isinstance(frames, list) and frames:
        show_api_response(frames[-1])


def process_video_locally(engine: PpeInferenceEngine, uploaded_file: object, event_log: list[dict[str, object]]) -> None:
    import cv2

    local_event_logger = EventLogger(OUTPUT_DIR / "events.db")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as source:
        source.write(uploaded_file.getbuffer())
        source_path = Path(source.name)

    capture = cv2.VideoCapture(str(source_path))
    if not capture.isOpened():
        source_path.unlink(missing_ok=True)
        raise RuntimeError("Unable to open uploaded video")
    output_path = OUTPUT_DIR / f"{source_path.stem}_annotated.mp4"
    writer = None
    try:
        frame_placeholder = st.empty()
        status_placeholder = st.empty()
        while True:
            success, frame = capture.read()
            if not success:
                break
            annotated, detections, status = engine.predict_frame(frame)
            workers, summary = compliance_for(detections)
            for worker in workers:
                for violation_type in worker.missing_ppe:
                    event_log.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "violation_type": violation_type,
                        "confidence": next(
                            (item.confidence for item in worker.detections
                                if MISSING_LABELS.get(item.class_name.casefold()) == violation_type), 0.0
                        ),
                        "affected_workers": 1,
                    })
            if summary.workers_with_violations:
                local_event_logger.record(
                    "webcam",
                    [item.class_name for item in detections],
                    max((item.confidence for item in detections), default=0.0),
                    "VIOLATION",
                    summary.total_violations,
                    [
                        {"class_name": item.class_name, "confidence": item.confidence}
                        for item in detections
                    ],
                )
            if writer is None:
                height, width = annotated.shape[:2]
                writer = cv2.VideoWriter(
                    str(output_path), cv2.VideoWriter_fourcc(*"mp4v"),
                    capture.get(cv2.CAP_PROP_FPS) or 24.0, (width, height)
                )
            writer.write(annotated)
            frame_placeholder.image(annotated, channels="BGR", use_container_width=True)
            status_placeholder.write(
                f"{'VIOLATION DETECTED' if summary.workers_with_violations else 'SAFE'} | "
                f"people: {summary.total_people} | violations: {summary.total_violations}"
            )
    finally:
        capture.release()
        if writer is not None:
            writer.release()
        source_path.unlink(missing_ok=True)
    st.success(f"Annotated video saved to {output_path}")


def run_live_camera(engine: PpeInferenceEngine, event_log: list[dict[str, object]]) -> None:
    import cv2

    local_event_logger = EventLogger(OUTPUT_DIR / "events.db")
    capture = cv2.VideoCapture(0)
    if not capture.isOpened():
        raise RuntimeError("Unable to open webcam 0")
    try:
        while True:
            success, frame = capture.read()
            if not success:
                raise RuntimeError("Webcam stopped returning frames")
            annotated, detections, _ = engine.predict_frame(frame)
            workers, summary = compliance_for(detections)
            for worker in workers:
                for violation_type in worker.missing_ppe:
                    event_log.append({
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "violation_type": violation_type,
                        "confidence": 0.0,
                        "affected_workers": 1,
                    })
            if summary.workers_with_violations:
                local_event_logger.record(
                    "webcam",
                    [item.class_name for item in detections],
                    max((item.confidence for item in detections), default=0.0),
                    "VIOLATION",
                    summary.total_violations,
                    [
                        {"class_name": item.class_name, "confidence": item.confidence}
                        for item in detections
                    ],
                )
            status = "VIOLATION DETECTED" if summary.workers_with_violations else "SAFE"
            cv2.putText(annotated, status, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow("Industrial Safety AI - press Q or Esc to stop", annotated)
            if cv2.waitKey(1) & 0xFF in {27, ord("q"), ord("Q")}:
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


def main() -> None:
    st.set_page_config(page_title="Industrial Safety AI", page_icon="🦺", layout="wide")
    st.title("Industrial Safety AI")
    st.caption(f"Inference backend: {API_BASE_URL}")
    show_backend_status()
    confidence = st.sidebar.slider("Confidence", 0.05, 0.95, 0.25, 0.05)
    iou = st.sidebar.slider("IoU", 0.05, 0.95, 0.45, 0.05)
    if "event_log" not in st.session_state:
        st.session_state.event_log = []

    image_file = st.file_uploader("Upload image", type=["jpg", "jpeg", "png", "bmp", "webp"])
    video_file = st.file_uploader("Upload video", type=["mp4", "avi", "mov", "mkv", "webm"])
    if image_file is not None:
        try:
            process_image(image_file, confidence, iou)
        except RuntimeError as error:
            st.error(str(error))
    if video_file is not None and st.button("Process uploaded video"):
        try:
            process_video(video_file, confidence, iou)
        except RuntimeError as error:
            st.error(str(error))
    if st.button("Start live camera"):
        try:
            engine = PpeInferenceEngine(MODEL_PATH, confidence, iou)
            run_live_camera(engine, st.session_state.event_log)
        except (FileNotFoundError, RuntimeError, ValueError) as error:
            st.error(str(error))
    if st.session_state.event_log:
        st.subheader("Event log")
        st.dataframe(st.session_state.event_log, use_container_width=True, hide_index=True)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=["timestamp", "violation_type", "confidence", "affected_workers"])
        writer.writeheader()
        writer.writerows(st.session_state.event_log)
        st.download_button("Download event log CSV", output.getvalue(), "ppe_events.csv", "text/csv")
    st.subheader("Detection history")
    show_event_history()
    st.caption("AI detections are decision-support signals and require site-specific validation before safety-critical deployment.")


if __name__ == "__main__":
    main()
