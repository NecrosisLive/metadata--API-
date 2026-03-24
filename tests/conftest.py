"""Shared test fixtures for the metadata inventory test suite."""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.main import app


@pytest_asyncio.fixture
async def mock_db():
    """Provide a mocked MongoDB database for tests."""
    client = AsyncMongoMockClient()
    db = client["test_metadata_inventory"]

    # Create the same index as production
    await db["metadata"].create_index("url", unique=True)

    with patch("app.database._db", db), \
         patch("app.database._client", client), \
         patch("app.services.get_collection", return_value=db["metadata"]), \
         patch("app.database.get_collection", return_value=db["metadata"]):
        yield db

    client.close()


@pytest_asyncio.fixture
async def async_client(mock_db):
    """Provide an async HTTP test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
