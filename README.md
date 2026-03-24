# HTTP Metadata Inventory

A FastAPI service that collects and caches HTTP metadata (headers, cookies, and page source) for any given URL, backed by MongoDB.

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────┐
│  Client      │─────▶│  FastAPI API  │─────▶│  MongoDB  │
│  (HTTP)      │◀─────│  (uvicorn)   │◀─────│          │
└─────────────┘      └──────┬───────┘      └──────────┘
                            │
                     ┌──────▼───────┐
                     │  Background   │
                     │  Worker       │
                     │  (asyncio)    │
                     └──────────────┘
```

**Key components:**

- **`app/config.py`** — Settings via environment variables (pydantic-settings)
- **`app/database.py`** — MongoDB connection lifecycle and collection access
- **`app/models.py`** — Pydantic models for validation and serialization
- **`app/services.py`** — Business logic: fetch metadata, store/retrieve from DB
- **`app/worker.py`** — Async background task orchestration (no external queues)
- **`app/routes.py`** — API endpoint definitions
- **`app/main.py`** — FastAPI app with lifespan management

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

### Run the service

```bash
docker-compose up --build
```

The API will be available at **http://localhost:8000**.

### API Documentation

FastAPI auto-generates interactive docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### `POST /metadata/`

Collect metadata for a given URL immediately.

**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response (201 Created):**
```json
{
  "url": "https://example.com",
  "headers": { "content-type": "text/html; charset=UTF-8", "..." : "..." },
  "cookies": {},
  "page_source": "<!doctype html>...",
  "collected_at": "2024-01-15T10:30:00"
}
```

**Error (502 Bad Gateway):** Returned if the target URL cannot be fetched.

### `GET /metadata/?url=<URL>`

Retrieve cached metadata for a URL.

**Cache hit (200 OK):** Returns the full metadata record.

**Cache miss (202 Accepted):**
```json
{
  "message": "Request accepted. Metadata collection has been queued.",
  "url": "https://example.com",
  "status": "pending"
}
```

The metadata will be collected asynchronously in the background. Subsequent GET requests will return the data once collection is complete.

### `GET /health`

Health check endpoint. Returns `{"status": "healthy"}`.

## Configuration

| Environment Variable | Default                     | Description                    |
|---------------------|-----------------------------|--------------------------------|
| `MONGODB_URI`       | `mongodb://localhost:27017` | MongoDB connection string      |
| `MONGODB_DB_NAME`   | `metadata_inventory`        | Database name                  |
| `REQUEST_TIMEOUT`   | `10.0`                      | HTTP request timeout (seconds) |

## Running Tests

### With Docker (recommended)

```bash
docker-compose run --rm api python -m pytest -v
```

### Locally

```bash
pip install -r requirements.txt
python -m pytest -v
```

Tests use `mongomock-motor` to mock MongoDB — no running database is required.

## Design Decisions

- **Async background tasks via `asyncio.create_task`**: No external message queue needed. Tasks are deduplicated per URL to avoid redundant work.
- **Upsert strategy**: `store_metadata` uses MongoDB `update_one` with `upsert=True` to handle both inserts and updates, preventing duplicate documents.
- **Unique index on `url`**: Ensures fast lookups and data integrity at the database level.
- **Separation of concerns**: Routes handle HTTP, services handle business logic, worker handles orchestration — each layer is independently testable.
- **Non-root Docker user**: The container runs as `appuser` for security best practices.
- **Health checks on MongoDB**: Docker Compose waits for MongoDB to be ready before starting the API.

## License

MIT
