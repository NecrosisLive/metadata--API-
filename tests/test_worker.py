"""Tests for the background worker module."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.worker import _pending_tasks, enqueue_collection, shutdown_worker


@pytest.mark.asyncio
async def test_enqueue_collection_creates_task():
    """enqueue_collection creates a background asyncio task."""
    with patch("app.worker.collect_and_store", new_callable=AsyncMock) as mock_collect:
        await enqueue_collection("https://example.com")

        # Give the task a moment to start
        await asyncio.sleep(0.1)

    mock_collect.assert_awaited_once_with("https://example.com")


@pytest.mark.asyncio
async def test_enqueue_collection_deduplicates():
    """enqueue_collection does not create duplicate tasks for the same URL."""
    # Create a slow task that won't finish immediately
    slow_future = asyncio.Future()

    with patch("app.worker.collect_and_store", new_callable=AsyncMock, side_effect=lambda _: slow_future):
        await enqueue_collection("https://example.com")
        await enqueue_collection("https://example.com")  # Should be skipped

    # Clean up
    slow_future.set_result(None)
    await asyncio.sleep(0.1)
    _pending_tasks.clear()


@pytest.mark.asyncio
async def test_enqueue_collection_handles_error():
    """enqueue_collection handles errors in the background task gracefully."""
    with patch("app.worker.collect_and_store", new_callable=AsyncMock, side_effect=Exception("DB error")):
        await enqueue_collection("https://failing.example.com")
        await asyncio.sleep(0.1)

    # Task should be cleaned up from _pending_tasks even after failure
    assert "https://failing.example.com" not in _pending_tasks


@pytest.mark.asyncio
async def test_shutdown_worker_cancels_tasks():
    """shutdown_worker cancels all pending background tasks."""
    slow_future = asyncio.Future()

    with patch("app.worker.collect_and_store", new_callable=AsyncMock, side_effect=lambda _: slow_future):
        await enqueue_collection("https://example.com")
        await shutdown_worker()

    assert len(_pending_tasks) == 0
