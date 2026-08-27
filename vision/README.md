# Vision runtime

Phase 2 processes one webcam or local video file at a time. It keeps video input,
person tracking, PPE-model inference, PPE-to-worker association, and rendering in
separate modules.

`tracking.py` is the only person detection path: it calls an Ultralytics detector with
`persist=True` and the selected `bytetrack.yaml` or `botsort.yaml` tracker. Do not add a
second person detector beside it.

`detection.py` is intentionally limited to PPE-specific inference. A PPE model must be
configured with `VISION_PPE_MODEL` and an explicit `VISION_PPE_CLASS_MAP`; otherwise
worker helmet, vest, and shoe status is rendered as unknown (`?`), not as missing.

Run the runtime with `safety-vision` after configuring `VISION_SOURCE`.
