"""
Pydantic v2 schemas for request validation and response serialisation.
Keeps API contracts separate from database models.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Pricing  (defined first so AIGeneratedListing can reference it directly)
# ---------------------------------------------------------------------------

class PriceSuggestionRequest(BaseModel):
    brand: str
    category: str
    condition: str = Field(..., description="e.g. new, like_new, good, fair, poor")


class PriceSuggestionResponse(BaseModel):
    recommended_price: float
    min_price: float
    max_price: float


# ---------------------------------------------------------------------------
# Listing – Generate
# ---------------------------------------------------------------------------

class ListingGenerateRequest(BaseModel):
    """
    Input to the AI generation endpoint.
    A user_id is required so the backend can immediately persist a draft listing,
    allowing the frontend to jump straight to publish without a separate create call.

    Optional stock field allows setting initial quantity (defaults to 1).
    Optional additional_image_urls for supporting multiple product images.
    """
    image_url: str = Field(..., description="Publicly accessible URL of the primary product image (used for AI analysis)")
    user_id: uuid.UUID = Field(..., description="Owner of the draft listing to be created")
    stock: int = Field(1, ge=1, description="Initial quantity in stock (defaults to 1)")
    additional_image_urls: list[str] = Field(default_factory=list, description="Additional product image URLs (optional)")


class AIGeneratedListing(BaseModel):
    """
    Response from POST /api/v1/listings/generate.

    Contains all AI-extracted attributes plus an auto-computed price_suggestion
    and the listing_id of the draft that was saved to the database.
    The frontend can preview, optionally call PATCH /{id} to apply edits,
    then POST /{id}/publish — no need to manually re-create the listing.
    """
    listing_id: uuid.UUID           # ID of the auto-created draft in the DB
    title: str
    description: str
    hashtags: list[str]
    brand: Optional[str] = None
    category: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    color: Optional[str] = None
    condition_estimate: Optional[str] = None
    image_urls: list[str] = Field(default_factory=list)
    stock: int = Field(1, ge=1)  # Initial stock quantity
    # Auto-computed from brand + category + condition_estimate
    price_suggestion: Optional[PriceSuggestionResponse] = None


# ---------------------------------------------------------------------------
# Listing – Create (manual path, still supported)
# ---------------------------------------------------------------------------

class ListingCreateRequest(BaseModel):
    """Payload for manually creating a new listing."""
    user_id: uuid.UUID
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    color: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    price: Optional[float] = Field(None, ge=0)
    stock: int = Field(1, ge=1)


# ---------------------------------------------------------------------------
# Listing – Update (PATCH)
# ---------------------------------------------------------------------------

class ListingUpdateRequest(BaseModel):
    """
    All fields optional — only supplied fields are updated.
    Used by the frontend after the AI-generate preview step.
    """
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    color: Optional[str] = None
    hashtags: Optional[list[str]] = None
    image_urls: Optional[list[str]] = None
    price: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=1)


# ---------------------------------------------------------------------------
# Listing – Stock update
# ---------------------------------------------------------------------------

class ListingStockUpdateRequest(BaseModel):
    """Payload for the PATCH /{id}/stock endpoint."""
    quantity_sold: int = Field(..., ge=1, description="Number of units sold")


class ListingRepostRequest(BaseModel):
    """Payload for POST /{id}/repost endpoint."""
    stock: int = Field(1, ge=1, description="Stock quantity for the reposted listing")


# ---------------------------------------------------------------------------
# Listing – Response
# ---------------------------------------------------------------------------

class ListingResponse(BaseModel):
    """Public representation of a listing returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    size: Optional[str] = None
    condition: Optional[str] = None
    material: Optional[str] = None
    style: Optional[str] = None
    color: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    price: Optional[float] = None
    stock: int
    status: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Listing – Paginated list response
# ---------------------------------------------------------------------------

class ListingListResponse(BaseModel):
    """Paginated wrapper returned by GET /api/v1/listings."""
    items: list[ListingResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------

class JobResponse(BaseModel):
    """Public representation of an automation job."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_id: uuid.UUID
    job_type: str
    status: str
    attempts: int
    error_message: Optional[str] = None
    created_at: datetime


class QueuedJobResponse(BaseModel):
    """Minimal response returned immediately after enqueueing a background job."""
    job_id: uuid.UUID
    status: str = "queued"
