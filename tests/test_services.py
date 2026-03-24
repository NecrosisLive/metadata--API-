"""Tests for the metadata collection service layer."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models import MetadataDocument
from app.services import fetch_metadata, get_metadata_by_url, store_metadata


@pytest.mark.asyncio
async def test_fetch_metadata_success():
    """fetch_metadata returns a completed document on success."""
    mock_response = httpx.Response(
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        text="<html><body>Test</body></html>",
        request=httpx.Request("GET", "https://example.com"),
    )

    with patch("app.services.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await fetch_metadata("https://example.com")

    assert result.status == "completed"
    assert result.url == "https://example.com"
    assert "content-type" in result.headers
    assert result.page_source == "<html><body>Test</body></html>"


@pytest.mark.asyncio
async def test_fetch_metadata_timeout():
    """fetch_metadata returns a failed document on timeout."""
    with patch("app.services.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.side_effect = httpx.TimeoutException("timed out")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await fetch_metadata("https://slow.example.com")

    assert result.status == "failed"
    assert "Timeout" in result.error


@pytest.mark.asyncio
async def test_fetch_metadata_request_error():
    """fetch_metadata returns a failed document on connection error."""
    with patch("app.services.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.side_effect = httpx.ConnectError("Connection refused")
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance

        result = await fetch_metadata("https://down.example.com")

    assert result.status == "failed"
    assert result.error is not None


@pytest.mark.asyncio
async def test_store_metadata(mock_db):
    """store_metadata inserts a document into the collection."""
    doc = MetadataDocument(
        url="https://example.com",
        headers={"server": "nginx"},
        cookies={},
        page_source="<html></html>",
        collected_at=datetime(2024, 1, 1),
        status="completed",
    )

    await store_metadata(doc)

    stored = await mock_db["metadata"].find_one({"url": "https://example.com"})
    assert stored is not None
    assert stored["headers"]["server"] == "nginx"


@pytest.mark.asyncio
async def test_store_metadata_upsert(mock_db):
    """store_metadata updates an existing document instead of duplicating."""
    doc1 = MetadataDocument(
        url="https://example.com",
        headers={"server": "nginx"},
        page_source="<html>v1</html>",
        collected_at=datetime(2024, 1, 1),
        status="completed",
    )
    doc2 = MetadataDocument(
        url="https://example.com",
        headers={"server": "apache"},
        page_source="<html>v2</html>",
        collected_at=datetime(2024, 6, 1),
        status="completed",
    )

    await store_metadata(doc1)
    await store_metadata(doc2)

    count = await mock_db["metadata"].count_documents({"url": "https://example.com"})
    assert count == 1

    stored = await mock_db["metadata"].find_one({"url": "https://example.com"})
    assert stored["page_source"] == "<html>v2</html>"


@pytest.mark.asyncio
async def test_get_metadata_by_url_found(mock_db):
    """get_metadata_by_url returns the document when it exists."""
    await mock_db["metadata"].insert_one({
        "url": "https://example.com",
        "headers": {"server": "nginx"},
        "cookies": {},
        "page_source": "<html></html>",
        "collected_at": datetime(2024, 1, 1),
        "status": "completed",
        "error": None,
    })

    result = await get_metadata_by_url("https://example.com")
    assert result is not None
    assert result.url == "https://example.com"
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_get_metadata_by_url_not_found(mock_db):
    """get_metadata_by_url returns None when the URL is not in the database."""
    result = await get_metadata_by_url("https://nonexistent.example.com")
    assert result is None
