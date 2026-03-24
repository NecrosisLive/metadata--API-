"""this is the business logic for fetching and storing URL metadata."""

import logging
from datetime import UTC, datetime

import httpx

from app.config import settings
from app.database import get_collection
from app.models import MetadataDocument

logger = logging.getLogger(__name__)


async def fetch_metadata(url: str) -> MetadataDocument:
    """
    Fetch headers, cookies, and page source from the given URL.
    Returns a MetadataDocument with the collected data or error details.
    """
    try:
        async with httpx.AsyncClient(
            timeout=settings.request_timeout,
            follow_redirects=True,
            verify=False,  # Disable SSL verification for simplicity; consider enabling in production
        ) as client:
            response = await client.get(url)

        headers = dict(response.headers)
        cookies = {name: value for name, value in response.cookies.items()}
        page_source = response.text

        return MetadataDocument(
            url=url,
            headers=headers,
            cookies=cookies,
            page_source=page_source,
            collected_at=datetime.now(UTC),
            status="completed",
        )

    except httpx.TimeoutException:
        logger.error("Timeout fetching URL: %s", url)
        return MetadataDocument(
            url=url,
            collected_at=datetime.now(UTC),
            status="failed",
            error=f"Timeout after {settings.request_timeout}s",
        )
    except httpx.RequestError as exc:
        logger.error("Request error for URL %s: %s", url, exc)
        return MetadataDocument(
            url=url,
            collected_at=datetime.now(UTC),
            status="failed",
            error=str(exc),
        )
    except Exception as exc:
        logger.error("Unexpected error fetching URL %s: %s", url, exc)
        return MetadataDocument(
            url=url,
            collected_at=datetime.now(UTC),
            status="failed",
            error=f"Unexpected error: {exc}",
        )


async def store_metadata(doc: MetadataDocument) -> None:
    """Insert or update a metadata document in MongoDB."""
    collection = get_collection()
    await collection.update_one(
        {"url": doc.url},
        {"$set": doc.to_mongo()},
        upsert=True,
    )


async def get_metadata_by_url(url: str) -> MetadataDocument | None:
    """Retrieve a metadata document by URL. Returns None if not found."""
    collection = get_collection()
    doc = await collection.find_one({"url": url})
    if doc is None:
        return None
    return MetadataDocument.from_mongo(doc)


async def collect_and_store(url: str) -> MetadataDocument:
    """Fetch metadata for a URL and persist it to the database."""
    metadata = await fetch_metadata(url)
    await store_metadata(metadata)
    return metadata
