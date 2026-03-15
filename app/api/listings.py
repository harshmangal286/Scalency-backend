"""
Listings API – AI generation, CRUD, publishing, reposting, and stock management.

Workflow:
  POST /generate        → AI generates attributes + saves draft → returns listing_id
  GET  /{id}            → frontend fetches full draft for preview
  PATCH /{id}           → user edits title / price / etc.
  POST /{id}/publish    → enqueues Celery publish job
  POST /{id}/repost     → enqueues Celery repost job
  PATCH /{id}/stock     → records a sale; auto-reposts when stock > 0
"""

import uuid
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.constants import UPLOADS_DIR, ALLOWED_IMAGE_TYPES
from app.models import (    # package import triggers configure_mappers()
    AutomationJob, JobStatus, JobType,
    Listing, ListingStatus, User,
)
from app.schemas.listing_schema import (
    AIGeneratedListing,
    ListingCreateRequest,
    ListingGenerateRequest,
    ListingListResponse,
    ListingRepostRequest,
    ListingResponse,
    ListingStockUpdateRequest,
    ListingUpdateRequest,
    JobResponse,
    QueuedJobResponse,
)
from app.services.ai_service import generate_and_save_draft
from app.services.pricing_service import suggest_price

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])

# Create uploads directory if it doesn't exist
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ---------------------------------------------------------------------------
# File Upload – store image and return URL
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    summary="Upload an image file (returns URL for use in /generate)",
    status_code=status.HTTP_200_OK,
)
async def upload_image(
    file: UploadFile = File(..., description="Image file (JPG, PNG, GIF, WebP)"),
) -> dict:
    """
    Accept file upload, validate, store, and return a URL.

    **Returns:**
    - `image_url`: URL to the stored image (can be used with /listings/generate)

    **Validation:**
    - File type must be image (JPEG, PNG, GIF, WebP)
    - Max size: 10MB (same as frontend limit)

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/v1/listings/upload \
      -F "file=@/path/to/image.jpg"
    ```
    """
    # Validate file type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type: {file.content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )

    # Read file and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File size exceeds {MAX_FILE_SIZE / 1024 / 1024}MB limit",
        )

    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = UPLOADS_DIR / unique_filename

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except IOError as exc:
        logger.exception("Failed to save upload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file",
        ) from exc

    # Return URL (frontend can use this with /generate endpoint)
    image_url = f"http://localhost:8000/api/v1/listings/uploads/{unique_filename}"
    return {
        "image_url": image_url,
        "filename": unique_filename,
        "size": len(content),
    }


# ---------------------------------------------------------------------------
# File Serving – serve uploaded images
# ---------------------------------------------------------------------------

@router.get(
    "/uploads/{filename}",
    summary="Retrieve uploaded image",
)
async def get_uploaded_image(filename: str):
    """
    Serve uploaded image file by filename.

    This endpoint allows accessing uploaded images via HTTP URL
    (which can be passed to /listings/generate).
    """
    from fastapi.responses import FileResponse

    file_path = UPLOADS_DIR / filename

    # Security: prevent directory traversal
    if not file_path.is_relative_to(UPLOADS_DIR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileResponse(
        file_path,
        media_type="image/jpeg",  # Will be overridden by actual file type
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------------------------------------------------------------------------
# AI Generation  – creates draft automatically
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=AIGeneratedListing,
    summary="Generate listing attributes from a product image and save as draft",
    status_code=status.HTTP_201_CREATED,
)
async def generate_listing(
    body: ListingGenerateRequest,
    db: Session = Depends(get_db),
) -> AIGeneratedListing:
    """
    Calls the AI model with the image URL, persists a draft listing in the DB,
    and returns all generated attributes alongside the `listing_id`.

    The frontend should:
    1. Display the returned attributes as a preview.
    2. Optionally call PATCH /{listing_id} if the user wants to edit.
    3. Call POST /{listing_id}/publish when the user is ready.
    """
    # Validate user exists BEFORE calling the AI to avoid wasting API credits
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"User '{body.user_id}' not found. "
                "Create a user first via POST /api/v1/users, then use the returned id."
            ),
        )

    try:
        result = await generate_and_save_draft(
            image_url=body.image_url,
            user_id=body.user_id,
            db=db,
            stock=body.stock,
            additional_image_urls=body.additional_image_urls,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("AI generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service unavailable. Please try again later.",
        ) from exc

    return result


# ---------------------------------------------------------------------------
# List Listings
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=ListingListResponse,
    summary="List listings, with optional filtering and pagination",
)
def list_listings(
    listing_status: Optional[str] = Query(None, alias="status", description="Filter by status: draft, published, sold, archived"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: Session = Depends(get_db),
) -> ListingListResponse:
    """
    Returns a paginated list of listings.
    Optionally filter by `status`.
    """
    query = db.query(Listing)
    if listing_status is not None:
        query = query.filter(Listing.status == listing_status)
    total = query.count()
    items = query.order_by(Listing.created_at.desc()).offset(offset).limit(limit).all()
    return ListingListResponse(items=items, total=total, limit=limit, offset=offset)


# ---------------------------------------------------------------------------
# Get Listing
# ---------------------------------------------------------------------------

@router.get(
    "/{listing_id}",
    response_model=ListingResponse,
    summary="Fetch full listing details",
)
def get_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ListingResponse:
    """Returns the full listing record, including all AI-extracted attributes."""
    return _get_listing_or_404(db, listing_id)


# ---------------------------------------------------------------------------
# Get Jobs for a Listing
# ---------------------------------------------------------------------------

@router.get(
    "/{listing_id}/jobs",
    response_model=list[JobResponse],
    summary="Get all automation jobs for a listing",
)
def get_listing_jobs(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    """
    Returns all AutomationJob records tied to the listing, newest first.
    Use this to poll whether a publish or repost job has completed.
    """
    _get_listing_or_404(db, listing_id)
    return (
        db.query(AutomationJob)
        .filter(AutomationJob.listing_id == listing_id)
        .order_by(AutomationJob.created_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# Create Listing  (manual path – still supported)
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=ListingResponse,
    summary="Manually create a new listing",
    status_code=status.HTTP_201_CREATED,
)
def create_listing(
    body: ListingCreateRequest,
    db: Session = Depends(get_db),
) -> ListingResponse:
    """
    Persists a new listing in DRAFT status.
    If no price is provided, auto-suggests one from brand/category/condition.
    """
    if not db.query(User).filter(User.id == body.user_id).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"User '{body.user_id}' not found. "
                "Create a user first via POST /api/v1/users."
            ),
        )

    price = body.price
    if price is None and body.brand and body.category and body.condition:
        suggestion = suggest_price(body.brand, body.category, body.condition)
        price = suggestion.recommended_price

    listing = Listing(
        user_id=body.user_id,
        title=body.title,
        description=body.description,
        brand=body.brand,
        category=body.category,
        size=body.size,
        condition=body.condition,
        material=body.material,
        style=body.style,
        color=body.color,
        hashtags=body.hashtags or [],
        image_urls=body.image_urls or [],
        price=price,
        stock=body.stock,
        status=ListingStatus.DRAFT,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# Update Listing  (PATCH – partial update)
# ---------------------------------------------------------------------------

@router.patch(
    "/{listing_id}",
    response_model=ListingResponse,
    summary="Partially update a listing (e.g. after AI preview editing)",
)
def update_listing(
    listing_id: uuid.UUID,
    body: ListingUpdateRequest,
    db: Session = Depends(get_db),
) -> ListingResponse:
    """
    Applies only the fields that are explicitly set in the request body.
    Designed for the post-generate preview step where the user may adjust
    title, price, size, or any other attribute before publishing.
    """
    listing = _get_listing_or_404(db, listing_id)

    # Iterate over provided fields only (exclude_unset prevents accidental nulls)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(listing, field, value)

    db.commit()
    db.refresh(listing)
    return listing


# ---------------------------------------------------------------------------
# Publish Listing
# ---------------------------------------------------------------------------

@router.post(
    "/{listing_id}/publish",
    response_model=QueuedJobResponse,
    summary="Publish a listing via a background job",
    status_code=status.HTTP_202_ACCEPTED,
)
def publish_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> QueuedJobResponse:
    """
    Enqueues a Celery task to publish the listing.
    Returns a job_id you can poll via GET /api/v1/jobs/{job_id}.
    """
    listing = _get_listing_or_404(db, listing_id)

    if listing.status == ListingStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Listing is already published.",
        )

    job = AutomationJob(
        listing_id=listing.id,
        job_type=JobType.PUBLISH,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.tasks.publish_task import publish_listing_task  # avoid circular import

    publish_listing_task.delay(str(listing.id), str(job.id))
    return QueuedJobResponse(job_id=job.id)


# ---------------------------------------------------------------------------
# Repost Listing
# ---------------------------------------------------------------------------

@router.post(
    "/{listing_id}/repost",
    response_model=QueuedJobResponse,
    summary="Repost a listing (clone + republish) via a background job",
    status_code=status.HTTP_202_ACCEPTED,
)
def repost_listing(
    listing_id: uuid.UUID,
    body: ListingRepostRequest,
    db: Session = Depends(get_db),
) -> QueuedJobResponse:
    """
    Enqueues a Celery task that clones the listing and republishes the clone.
    Allows specifying stock quantity for the reposted listing.
    Returns a job_id you can poll via GET /api/v1/jobs/{job_id}.
    """
    listing = _get_listing_or_404(db, listing_id)

    job = AutomationJob(
        listing_id=listing.id,
        job_type=JobType.REPOST,
        status=JobStatus.PENDING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    from app.tasks.repost_task import repost_listing_task

    repost_listing_task.delay(str(listing.id), str(job.id), body.stock)
    return QueuedJobResponse(job_id=job.id)


# ---------------------------------------------------------------------------
# Update Stock
# ---------------------------------------------------------------------------

@router.patch(
    "/{listing_id}/stock",
    response_model=ListingResponse,
    summary="Reduce stock after a sale; auto-repost if stock remains",
)
def update_stock(
    listing_id: uuid.UUID,
    body: ListingStockUpdateRequest,
    db: Session = Depends(get_db),
) -> ListingResponse:
    """
    Decrements stock by `quantity_sold`.
    - Stock reaches 0  → status set to "sold".
    - Stock still > 0  → automatic repost job queued.
    """
    listing = _get_listing_or_404(db, listing_id)

    if body.quantity_sold > listing.stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot sell {body.quantity_sold} units; only {listing.stock} in stock.",
        )

    listing.stock -= body.quantity_sold

    if listing.stock == 0:
        listing.status = ListingStatus.SOLD
        db.commit()
        db.refresh(listing)
    else:
        db.commit()
        db.refresh(listing)

        repost_job = AutomationJob(
            listing_id=listing.id,
            job_type=JobType.REPOST,
            status=JobStatus.PENDING,
        )
        db.add(repost_job)
        db.commit()
        db.refresh(repost_job)

        from app.tasks.repost_task import repost_listing_task

        repost_listing_task.delay(str(listing.id), str(repost_job.id))

    return listing


# ---------------------------------------------------------------------------
# Delete Listing
# ---------------------------------------------------------------------------

@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a listing",
)
def delete_listing(
    listing_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    """
    Deletes a listing and all associated data.
    Can delete listings in any status (draft, published, sold, etc).
    """
    listing = _get_listing_or_404(db, listing_id)

    db.delete(listing)
    db.commit()

    logger.info("Listing %s deleted successfully.", listing_id)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_listing_or_404(db: Session, listing_id: uuid.UUID) -> Listing:
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Listing {listing_id} not found.",
        )
    return listing
