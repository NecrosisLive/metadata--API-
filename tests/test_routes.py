"""Tests for API route endpoints."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models import MetadataDocument


@pytest.mark.asyncio
async def test_health_check(async_client):
    """Health endpoint returns 200."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_post_metadata_success(async_client, mock_db):
    """POST /metadata/ collects and returns metadata for a valid URL."""
    fake_doc = MetadataDocument(
        url="https://example.com",
        headers={"content-type": "text/html"},
        cookies={"session": "abc123"},
        page_source="<html>Hello</html>",
        collected_at=datetime(2024, 1, 1),
        status="completed",
    )

    with patch("app.routes.collect_and_store", new_callable=AsyncMock, return_value=fake_doc):
        response = await async_client.post(
            "/metadata/",
            json={"url": "https://example.com"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["headers"]["content-type"] == "text/html"
    assert data["cookies"]["session"] == "abc123"
    assert data["page_source"] == "<html>Hello</html>"


@pytest.mark.asyncio
async def test_post_metadata_invalid_url(async_client):
    """POST /metadata/ with an invalid URL returns 422."""
    response = await async_client.post(
        "/metadata/",
        json={"url": "not-a-url"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_metadata_fetch_failure(async_client, mock_db):
    """POST /metadata/ returns 502 when the target URL cannot be fetched."""
    failed_doc = MetadataDocument(
        url="https://unreachable.example.com",
        collected_at=datetime(2024, 1, 1),
        status="failed",
        error="Connection refused",
    )

    with patch("app.routes.collect_and_store", new_callable=AsyncMock, return_value=failed_doc):
        response = await async_client.post(
            "/metadata/",
            json={"url": "https://unreachable.example.com"},
        )

    assert response.status_code == 502
    assert "Failed to fetch URL" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_metadata_cache_hit(async_client, mock_db):
    """GET /metadata/?url=... returns 200 when data exists in DB."""
    fake_doc = MetadataDocument(
        url="https://example.com",
        headers={"content-type": "text/html"},
        cookies={},
        page_source="<html>Cached</html>",
        collected_at=datetime(2024, 1, 1),
        status="completed",
    )

    with patch("app.routes.get_metadata_by_url", new_callable=AsyncMock, return_value=fake_doc):
        response = await async_client.get("/metadata/", params={"url": "https://example.com"})

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["page_source"] == "<html>Cached</html>"


@pytest.mark.asyncio
async def test_get_metadata_cache_miss(async_client, mock_db):
    """GET /metadata/?url=... returns 202 and queues background collection when not cached."""
    with patch("app.routes.get_metadata_by_url", new_callable=AsyncMock, return_value=None), \
         patch("app.routes.enqueue_collection", new_callable=AsyncMock) as mock_enqueue:
        response = await async_client.get("/metadata/", params={"url": "https://new.example.com"})

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert data["url"] == "https://new.example.com"
    mock_enqueue.assert_awaited_once_with("https://new.example.com")


@pytest.mark.asyncio
async def test_get_metadata_incomplete_record(async_client, mock_db):
    """GET /metadata/ returns 202 when the existing record is not yet completed."""
    pending_doc = MetadataDocument(
        url="https://example.com",
        collected_at=datetime(2024, 1, 1),
        status="in_progress",
    )

    with patch("app.routes.get_metadata_by_url", new_callable=AsyncMock, return_value=pending_doc), \
         patch("app.routes.enqueue_collection", new_callable=AsyncMock):
        response = await async_client.get("/metadata/", params={"url": "https://example.com"})

    assert response.status_code == 202
