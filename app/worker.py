"""Background worker for asynchronous metadata collection.

Uses asyncio tasks to handle cache-miss collection without blocking
the request-response cycle. No external queues or self-HTTP calls.
"""

import asyncio
import logging

from app.services import collect_and_store

logger = logging.getLogger(__name__)

# Track in-flight background tasks to prevent duplicate work
_pending_tasks: dict[str, asyncio.Task] = {}


async def enqueue_collection(url: str) -> None:
    """
    Schedule background metadata collection for a URL.

    If a collection task is already running for this URL, it is not duplicated.
    The task runs independently of the request-response cycle.
    """
    # Skip if already being collected
    if url in _pending_tasks and not _pending_tasks[url].done():
        logger.info("Collection already in progress for: %s", url)
        return

    task = asyncio.create_task(_collect_task(url))
    _pending_tasks[url] = task
    logger.info("Background collection enqueued for: %s", url)


async def _collect_task(url: str) -> None:
    """Internal coroutine that performs collection and cleans up tracking."""
    try:
        await collect_and_store(url)
        logger.info("Background collection completed for: %s", url)
    except Exception as exc:
        logger.error("Background collection failed for %s: %s", url, exc)
    finally:
        _pending_tasks.pop(url, None)


async def shutdown_worker() -> None:
    """Cancel all pending background tasks during shutdown."""
    for url, task in _pending_tasks.items():
        if not task.done():
            task.cancel()
            logger.info("Cancelled pending collection for: %s", url)
    _pending_tasks.clear()
