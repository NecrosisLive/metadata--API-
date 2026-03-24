"""FastAPI application entry point with lifespan management."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import close_db, connect_db
from app.routes import router
from app.worker import shutdown_worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of database and background workers."""
    logger.info("Starting up — connecting to MongoDB...")
    await connect_db()
    logger.info("MongoDB connected.")
    yield
    logger.info("Shutting down — cleaning up resources...")
    await shutdown_worker()
    await close_db()
    logger.info("Shutdown complete.")


app = FastAPI(
    title="HTTP Metadata Inventory",
    description=(
        "A service that collects and caches HTTP metadata (headers, cookies, "
        "and page source) for any given URL."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy"}
