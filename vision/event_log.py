"""Small local event log with SQLite as the durable MVP backend."""

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

FIELDS = ["timestamp", "source_type", "detected_classes", "confidence", "violation_status", "number_of_violations"]
SQLITE_SUFFIXES = {".db", ".sqlite", ".sqlite3"}


class EventLogger:
    """Persist structured inference events to SQLite or legacy CSV."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        if self.path.suffix.casefold() in SQLITE_SUFFIXES:
            self._initialize_database()

    def record(
        self,
        source_type: str,
        detected_classes: list[str],
        confidence: float,
        violation_status: str,
        number_of_violations: int,
        detections: list[dict[str, Any]] | None = None,
        output_reference: str | None = None,
    ) -> None:
        if self.path.suffix.casefold() in SQLITE_SUFFIXES:
            self._record_sqlite(
                source_type,
                detected_classes,
                confidence,
                violation_status,
                number_of_violations,
                detections,
                output_reference,
            )
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_type": source_type,
            "detected_classes": ";".join(sorted(set(detected_classes))),
            "confidence": f"{confidence:.4f}",
            "violation_status": violation_status,
            "number_of_violations": number_of_violations,
        }
        with self._lock, self.path.open("a", newline="", encoding="utf-8") as output:
            writer = csv.DictWriter(output, fieldnames=FIELDS)
            if output.tell() == 0:
                writer.writeheader()
            writer.writerow(row)

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return recent events in descending timestamp order."""
        bounded_limit = max(1, min(limit, 500))
        if self.path.suffix.casefold() not in SQLITE_SUFFIXES:
            if not self.path.is_file():
                return []
            with self.path.open(newline="", encoding="utf-8") as event_file:
                return list(csv.DictReader(event_file))[-bounded_limit:][::-1]
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                """SELECT id, timestamp, source_type, detected_classes, confidence,
                          violation_status, number_of_violations, detections, output_reference
                   FROM events ORDER BY id DESC LIMIT ?""",
                (bounded_limit,),
            ).fetchall()
        fields = [
            "id", "timestamp", "source_type", "detected_classes", "confidence",
            "violation_status", "number_of_violations", "detections", "output_reference",
        ]
        result = []
        for row in rows:
            event = dict(zip(fields, row, strict=True))
            event["detections"] = json.loads(event["detections"] or "[]")
            result.append(event)
        return result

    def _initialize_database(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    detected_classes TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    violation_status TEXT NOT NULL,
                    number_of_violations INTEGER NOT NULL,
                    detections TEXT NOT NULL DEFAULT '[]',
                    output_reference TEXT
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC)"
            )

    def _record_sqlite(
        self,
        source_type: str,
        detected_classes: list[str],
        confidence: float,
        violation_status: str,
        number_of_violations: int,
        detections: list[dict[str, Any]] | None,
        output_reference: str | None,
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path, timeout=30) as connection:
            connection.execute(
                """INSERT INTO events (
                    timestamp, source_type, detected_classes, confidence,
                    violation_status, number_of_violations, detections, output_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    timestamp,
                    source_type,
                    ";".join(sorted(set(detected_classes))),
                    confidence,
                    violation_status,
                    number_of_violations,
                    json.dumps(detections or [], separators=(",", ":")),
                    output_reference,
                ),
            )
