"""API route definitions for the metadata inventory service."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.models import (
    AcceptedResponse,
    ErrorResponse,
    MetadataResponse,
    URLRequest,
)
from app.services import collect_and_store, get_metadata_by_url
from app.worker import enqueue_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.post(
    "/",
    response_model=MetadataResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        502: {"model": ErrorResponse, "description": "Failed to fetch URL"},
    },
    summary="Collect metadata for a URL",
    description=(
        "Fetches the HTTP headers, cookies, and page source of the given URL "
        "and stores the collected data in MongoDB."
    ),
)
async def create_metadata(payload: URLRequest) -> MetadataResponse:
    """POST endpoint: fetch metadata for a URL and store it."""
    url = str(payload.url)

    metadata = await collect_and_store(url)

    if metadata.status == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch URL: {metadata.error}",
        )

    return MetadataResponse(
        url=metadata.url,
        headers=metadata.headers,
        cookies=metadata.cookies,
        page_source=metadata.page_source,
        collected_at=metadata.collected_at,
    )


@router.get(
    "/",
    response_model=MetadataResponse,
    responses={
        202: {"model": AcceptedResponse, "description": "Collection queued"},
    },
    summary="Retrieve metadata for a URL",
    description=(
        "Returns cached metadata if it exists in the database. "
        "If not found, returns 202 Accepted and triggers background collection."
    ),
)
async def get_metadata(url: str):
    """
    GET endpoint: return existing metadata or queue background collection.

    - If the record exists and is completed → return full metadata (200).
    - If the record is missing or still pending → return 202 and enqueue.
    """
    existing = await get_metadata_by_url(url)

    if existing and existing.status == "completed":
        return MetadataResponse(
            url=existing.url,
            headers=existing.headers,
            cookies=existing.cookies,
            page_source=existing.page_source,
            collected_at=existing.collected_at,
        )

    # Cache miss or incomplete — trigger background collection
    await enqueue_collection(url)

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=202,
        content=AcceptedResponse(url=url).model_dump(),
    )
