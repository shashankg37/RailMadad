# Rail Madad AI Backend

Rail Madad AI is the backend and AI orchestration layer for railway complaint triage. The project exposes FastAPI endpoints for authentication, uploads, complaint management, and AI-assisted analysis while keeping the frontend out of scope.

## Architecture

- FastAPI application in `app/main.py`
- SQLAlchemy models and Postgres/MariaDB-compatible schema in `app/models`
- Pydantic request/response contracts in `app/schemas`
- Service layer for storage, complaint operations, and AI inference in `app/services`
- Upload and complaint APIs under `app/api/v1`
- Redis-backed state and Cloudinary-compatible object storage behind the storage abstraction

## Environment setup

Create a local `.env` from the example and fill in values for your deployment:

```bash
cp .env.example .env
```

Required variables include:

- `DATABASE_URL`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `CLOUDINARY_*`
- `QWEN_*`
- `SARVAM_*`
- `YOLO_MODEL_PATH`
- `VIDEO_MAX_FRAMES`
- `VIDEO_SAMPLE_INTERVAL_SECONDS`
- `MAX_UPLOAD_SIZE_MB`

## YOLO model placement

The repository expects a trained YOLO model at `models/best.pt` by default. If the file is not present, the API raises a clear configuration error instead of fabricating detections. Place the trained model in the configured path before running image inference.

## External AI services

- YOLOv8: loaded once and reused through `YOLOService`
- EasyOCR: isolated through `OCRService`
- Qwen: hosted provider integration through `QwenClient`
- Sarvam AI: primary speech-to-text provider
- IndicLID + IndicTrans2: language detection and translation interfaces
- Whisper: fallback transcription path
- LangGraph orchestration: shared state and routing workflow helpers

## Database migration and schema

The project uses SQLAlchemy models and Alembic migrations. Typical workflow:

```bash
alembic upgrade head
```

Ensure `DATABASE_URL` points to your PostgreSQL instance for production deployments.

## Docker

The bundled Docker Compose stack launches:

- FastAPI API
- PostgreSQL
- Redis

```bash
docker compose up --build
```

The hosted Qwen model remains an external API dependency and is not downloaded into the container.

## Testing

Run the repository tests with:

```bash
pytest -q
```

The suite includes the backend contract tests and the AI pipeline safety/routing regression checks.

## Troubleshooting

- If YOLO fails, verify `models/best.pt` exists and the `YOLO_MODEL_PATH` setting is correct.
- If uploads fail, confirm the file type and size are within the configured limits.
- If AI provider calls fail, validate the API keys, base URLs, and timeout configuration.
- If Redis or Postgres are unhealthy in Docker, check the health checks and environment values.

## Notes

- Frontend code is intentionally not included in this repo.
- Secrets must never be committed to source control.
- The backend is designed so the frontend can connect later without architecture changes.
