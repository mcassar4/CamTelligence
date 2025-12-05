# CamTelligence

CamTelligence is a local-first, CPU-first pipeline that turns camera feeds into discrete person and vehicle events. It stores media on disk, metadata in Postgres, and exposes a small FastAPI + React UI for live and filtered views.

## Goals
- Ingest frames from RTSP/HTTP streams or local files.
- Detect motion, then run person/vehicle detection only when motion exists.
- Persist events and associated media (frames and crops).
- Expose a minimal API and UI for browsing events.
- Optionally send Telegram notifications.
- Enforce retention with a janitor process.

## Non-goals
- Continuous video recording (this complements a DVR, it does not replace it).
- Cloud inference or external brokers.
- Complex multi-user auth or access control.

## Repository layout
- `services/processor/` - multiprocess CV pipeline (ingestion -> detection -> event writers -> notifier).
- `services/core/` - shared DB models and session utilities for processor and API.
- `services/api/` - FastAPI service for events, media, settings, and health/metrics.
- `frontend/` - React UI for live events and basic filtering.
- `services/processor/CamT_processor/janitor/` - retention cleanup for DB rows and media files.
- `data/` - local volumes (media, inputs, postgres data, motion debug output).

## High-level flow
1. Ingestion polls RTSP/HTTP sources or local files and enqueues a `FrameJob` with JPEG bytes.
2. Detection runs per-camera motion gating. If motion is present, YOLO is run and detections are filtered by motion overlap.
3. Event writers persist frames and crops to disk and create DB rows for media assets and events.
4. Notifications are enqueued for Telegram delivery with a per-camera debounce.
5. The API serves events and media by ID, and the UI polls the API for live and filtered views.

## Processor architecture highlights
- Bounded queues enforce backpressure so ingestion slows when detection cannot keep up.
- Poison pills plus a shared stop event provide clean shutdown.
- The supervisor monitors worker processes and restarts them if they die.
- Notifications are best-effort: they are dropped when the queue is full to protect the core pipeline.

## Storage model
- Media is written to the filesystem under `MEDIA_ROOT`, split by type (`frame`, `person_crop`, `vehicle_crop`).
- Postgres stores metadata in `media_assets`, `person_events`, `vehicle_events`, and `notifications`.
- The API resolves media paths under `MEDIA_ROOT` and returns 404 when a file is missing.

## API and UI
### API endpoints
- `GET /admin/health` and `GET /admin/metrics`
- `GET /persons/recent?limit=...`
- `GET /vehicles/recent?limit=...`
- `POST /events/filter` with `camera`, `event_type`, `start`, `end`, `limit`
- `GET /media/{asset_id}`
- `PUT /settings` (upsert by key)

### UI pages
- Live Events: polls recent persons and vehicles every 5 seconds.
- Event Browser: submits filter queries and renders two lists.

## Configuration
Key environment variables (see `.env.example` for the full list):
- `CAMERA_SOURCES` - comma-separated sources, supports `name=source` form.
- `FRAME_POLL_INTERVAL` - seconds between polls.
- `QUEUE_SIZE` - max items per queue.
- `MEDIA_ROOT` - root directory for stored media.
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_DATABASE` or `DATABASE_URL`.
- `NOTIFICATIONS_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `NOTIFICATION_DEBOUNCE_SECONDS`.
- `VITE_API_BASE_URL` - frontend API base URL.
- Motion tuning: `MOTION_HISTORY`, `MOTION_KERNEL_SIZE`, `MOTION_MIN_AREA`, `MOTION_MAX_FOREGROUND_RATIO`.
- Retention: `RETENTION_ENABLED`, `RETENTION_DAYS`, `RETENTION_INTERVAL_SECONDS`.

## Running locally with Docker
1. Copy `.env.example` to `.env` and adjust as needed.
2. Start the stack:
   ```bash
   docker compose up --build
   ```
3. Access:
   - API: `http://localhost:8000`
   - UI: `http://localhost:3000`

## Data directories
- `data/media/` - persisted frames and crops
- `data/input/` - optional file-based ingestion
- `data/motion_results/` - motion debug output (only when debug logging is enabled)
- `data/postgres/` - local database storage

## Known tradeoffs
- Polling-based ingestion trades higher FPS for simplicity.
- The API is unauthenticated by default.
- Event queries are limit-only (no cursor/offset pagination).
- Filesystem and DB can drift if a write fails between the two.

## Roadmap ideas
- Higher-FPS ingestion using streaming rather than polling.
- Short event clips (pre/post-roll) instead of only single frames.
