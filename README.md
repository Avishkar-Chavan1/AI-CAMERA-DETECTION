# Industrial Safety AI Platform

## Current Progress

- [x] Streamlit dashboard
- [x] FastAPI inference backend
- [x] YOLO-based detection
- [x] Dockerfile
- [x] Docker image builds successfully
- [x] Docker container runs successfully
- [x] Backend health check
- [x] Local frontend-backend integration
- [x] Model loading verification inside Docker
- [ ] Full image inference validation against the live API
- [ ] Full video validation
- [ ] Live camera validation
- [ ] Docker Compose complete-system setup
- [ ] CI/CD
- [ ] Cloud deployment
- [ ] Production monitoring
- [ ] Horizontal scaling

FastAPI and Streamlit services for image, video, and local webcam PPE inference using
the supplied YOLO checkpoint. The API accepts media bytes only and never accepts a
client filesystem path.

## Architecture

- `backend/`: FastAPI application, environment configuration, logging, and API adapters.
- `vision/`: YOLO inference, compliance analysis, tracking, and local event logging.
- `dashboard/`: Streamlit image, video, and webcam interface.
- `tests/`: automated unit and API tests.
- `best.pt`: approved PPE model artifact expected at the repository root.
- `docker/`: Compose and dashboard/API-specific container definitions.

The API loads `best.pt` once during application startup. If the model is unavailable or
corrupt, the process stays available for diagnostics and `/api/v1/health` reports a
degraded state; inference requests return HTTP 503.

The verified `best.pt` class names are `helmet`, `gloves`, `vest`, `boots`, `goggles`,
`none`, `Person`, `no_helmet`, `no_goggle`, `no_gloves`, and `no_boots`. The model has no
`no_vest` or `no_goggles` class, so those violations cannot be detected explicitly.

## Requirements and installation

Use Python 3.11, 3.12, or 3.13. The model artifact is not downloaded automatically.
Place the approved checkpoint at `./best.pt` without modifying it.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,vision]"
Copy-Item .env.example .env
```

Alternatively, install runtime dependencies with `python -m pip install -r requirements.txt`.
The `.env` file is local-only and ignored by Git. No API keys are required by this version.

## Configuration

Configuration comes from environment variables and the repository-root `.env` file.
Important settings include:

- `PORT`: cloud/container HTTP port; defaults to `8000`.
- `API_BASE_URL`: dashboard URL for the FastAPI service; defaults to
  `http://localhost:8000` locally and is set to `http://api:8000` by Compose.
- `MODEL_PATH`: model path relative to the repository root; defaults to `best.pt` when
  unset. `VISION_PPE_MODEL` remains a backward-compatible alias.
- `API_CORS_ORIGINS`: JSON list of allowed dashboard origins.
- `API_AUTH_ENABLED`: enable API-key protection for inference endpoints; defaults to
  `false` for local development.
- `API_KEY`: secret expected in the `X-API-Key` header when authentication is enabled.
- `API_RATE_LIMIT` and `API_RATE_WINDOW_SECONDS`: per-client in-memory inference limit.
- `API_INFERENCE_TIMEOUT_SECONDS`: documented processing budget; video is additionally
  bounded by `API_MAX_VIDEO_FRAMES`.
- `API_REQUEST_TIMEOUT_SECONDS`: dashboard-to-API request timeout.
- `VISION_PPE_MIN_CONFIDENCE` and `VISION_IOU_THRESHOLD`: model defaults.
- `API_MAX_IMAGE_BYTES` and `API_MAX_VIDEO_BYTES`: upload limits.
- `API_MAX_VIDEO_FRAMES`: video processing limit.
- `API_EVENT_LOG_PATH`: relative CSV event-log path, defaulting to
  `runs/inference/events.db`.
- `LOG_LEVEL` and `LOG_JSON`: application logging controls.

See `.env.example` for the complete list. Do not place secrets in source or committed
environment files.

## Run the backend

From the repository root, use the production-style command:

```powershell
$env:PORT = "8000"
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port $env:PORT
```

On a cloud platform, use its exact start command with the platform-provided port:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

Endpoints:

- `GET /api/v1/health`: API and model readiness.
- `GET /api/v1/ready`: readiness probe; returns HTTP 503 when the model is unavailable.
- `GET /api/v1/metrics`: lightweight request, error, and inference timing counters.
- `GET /api/v1/events`: recent persisted inference events for the dashboard.
- `POST /api/v1/inference/image`: multipart field `file`; optional `confidence` and `iou`.
- `POST /api/v1/inference/video`: multipart field `file`; optional `confidence` and `iou`.
- `GET /docs`: interactive OpenAPI documentation.

Example image request:

```bash
curl -X POST "http://localhost:8000/api/v1/inference/image?confidence=0.25&iou=0.45" \
  -F "file=@test_inputs/images/example.jpg"
```

When authentication is enabled, include the API key:

```bash
curl -H "X-API-Key: $API_KEY" -X POST \
  "http://localhost:8000/api/v1/inference/image" \
  -F "file=@test_inputs/images/example.jpg"
```

Health and readiness remain public. Invalid or missing inference keys return HTTP 401;
excessive inference requests return HTTP 429. Image and video uploads are validated by
MIME type and extension, limited to the configured byte sizes, and video uploads are
streamed to temporary files that are deleted after processing.

Detection responses include `class`, `class_name`, `confidence`, `bounding_box`, and
`compliance_status` (`violation`, `compliant`, or `unknown`), alongside worker and
summary compliance results. Supported image and video MIME types are validated, uploads
are size-limited, and temporary video files are removed after processing.

Inference events are persisted to SQLite at `runs/inference/events.db` by default. Events
include source, detected classes, confidence, violation status, violation count, and
structured detection details. Uploaded video bytes are never stored in the database.

The default confidence threshold is `0.25` and the default IoU threshold is `0.45`.
The API supports JPEG, PNG, WEBP, and BMP images plus MP4, AVI, MOV, MKV, and WEBM
videos. A local webcam is supported by the host-side Streamlit application; the
containerized dashboard cannot provide a desktop OpenCV window or remote camera feed.

The compliance result is `VIOLATION` only for explicit violation detections, `SAFE` only
when every detected person has the required helmet and vest evidence, and `UNKNOWN` when
there is no person or insufficient PPE evidence. `SAFE` is not a safety certification.

## Run the dashboard

In a second terminal:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run dashboard\app.py --server.address 0.0.0.0 --server.port 8501
```

The dashboard supports image upload, video upload, and a webcam available to the machine
running Streamlit. It exposes confidence and IoU controls, separates worker violations
from compliant PPE evidence, and displays a downloadable local event log CSV.

## Docker

On Windows, install and start Docker Desktop before running Compose. The `docker`
command is provided by Docker Desktop and cannot be supplied by the Python virtual
environment. With `winget`, install it using:

```powershell
winget install --id Docker.DockerDesktop --source winget
```

Restart Windows if requested, launch Docker Desktop, and wait until its engine reports
ready. The API and dashboard Compose services use the same CPU-only inference setup.

Build and run the API image from the repository root:

```powershell
docker build -t industrial-safety-api .
docker run --rm -p 8000:8000 -e PORT=8000 -e APP_ENV=production industrial-safety-api
```

The root `Dockerfile` includes `backend/`, `vision/`, and `best.pt`, and starts Uvicorn
on `0.0.0.0` using `PORT`. It also includes a container healthcheck. For both services:

```powershell
docker compose -f docker/compose.yml up --build
```

Compose exposes the API on `${PORT:-8000}` and Streamlit on port 8501. CPU deployment
is supported; inference speed and memory use depend on the host and media resolution.
Inspect service logs with `docker compose -f docker/compose.yml logs -f api`.

The intended architecture is:

```text
Streamlit -> FastAPI -> YOLO inference -> detection and compliance result
```

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

The project uses CPU-only PyTorch intentionally. The main bottlenecks are model inference,
image resolution, and video frame count; benchmark representative site media before
choosing production hardware.

## Limitations and deployment notes

This is not a claim of production safety certification. The checkpoint's accuracy,
class coverage, camera angle tolerance, lighting tolerance, and false-positive/negative
rates must be validated against representative site data before operational use. The
local CSV event log is not a durable multi-instance database, and the API has no
distributed job queue or persistent object storage. Webcam capture
requires access to the host running the dashboard and is not provided by a remote API.

Before public deployment, provide `best.pt` through the image build context or a private
artifact mechanism, restrict network access as appropriate, add authentication and rate
limits, and replace local CSV storage with a managed database. Do not commit or push
automatically from this project.

The next deployment architecture is GitHub -> CI/CD -> Docker image -> container registry
-> AWS/Azure/GCP -> multiple backend instances -> load balancer -> monitoring/logging.
For industrial edge deployment, use Industrial Camera -> Edge Computer -> Docker ->
FastAPI + YOLO -> local dashboard/API -> optional cloud synchronization. Cloud deployment
and horizontal scaling are intentionally not implemented yet.
