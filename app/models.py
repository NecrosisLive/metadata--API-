"""Pydantic models for request/response validation and MongoDB documents."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


# ── Request Models ──────────────────────────────────────────────────────────

class URLRequest(BaseModel):
    """Input model for POST and GET endpoints."""
    url: HttpUrl


# ── Response Models ─────────────────────────────────────────────────────────

class MetadataResponse(BaseModel):
    """Full metadata record returned when data exists."""
    url: str
    headers: dict[str, str]
    cookies: dict[str, str]
    page_source: str
    collected_at: datetime


class AcceptedResponse(BaseModel):
    """Response returned when metadata collection is queued."""
    message: str = "Request accepted. Metadata collection has been queued."
    url: str
    status: str = "pending"


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str


# ── Internal / DB Models ───────────────────────────────────────────────────

class MetadataDocument(BaseModel):
    """Schema for the MongoDB metadata document."""
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    cookies: dict[str, str] = Field(default_factory=dict)
    page_source: str = ""
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "completed"  # "pending" | "in_progress" | "completed" | "failed"
    error: str | None = None

    def to_mongo(self) -> dict[str, Any]:
        """Convert to a MongoDB-compatible dict."""
        return self.model_dump()

    @classmethod
    def from_mongo(cls, doc: dict[str, Any]) -> "MetadataDocument":
        """Create instance from a MongoDB document."""
        doc.pop("_id", None)
        return cls(**doc)
