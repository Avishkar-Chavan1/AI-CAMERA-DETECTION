import csv

from vision.event_log import EventLogger


def test_event_logger_writes_header_and_event(tmp_path) -> None:
    path = tmp_path / "events.csv"
    EventLogger(path).record("image", ["Person", "no_helmet"], 0.81, "VIOLATION", 1)
    with path.open(newline="", encoding="utf-8") as event_file:
        rows = list(csv.DictReader(event_file))
    assert rows[0]["source_type"] == "image"
    assert rows[0]["detected_classes"] == "Person;no_helmet"
    assert rows[0]["number_of_violations"] == "1"


def test_event_logger_writes_and_reads_sqlite_event(tmp_path) -> None:
    logger = EventLogger(tmp_path / "events.db")
    logger.record(
        "video",
        ["person", "no_helmet"],
        0.91,
        "VIOLATION",
        1,
        [{"class_name": "no_helmet", "confidence": 0.91}],
        "runs/inference/example.mp4",
    )

    events = logger.list_recent()

    assert events[0]["source_type"] == "video"
    assert events[0]["detected_classes"] == "no_helmet;person"
    assert events[0]["detections"] == [{"class_name": "no_helmet", "confidence": 0.91}]
    assert events[0]["output_reference"] == "runs/inference/example.mp4"