"""
Jobs API – inspect automation job status.

Use GET /api/v1/jobs/{job_id} to poll whether a publish or repost
job has completed, without needing to check worker logs.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AutomationJob  # triggers configure_mappers()
from app.schemas.listing_schema import JobResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Fetch an automation job by ID",
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> JobResponse:
    """
    Returns the current state of an AutomationJob.

    Poll this endpoint after calling POST /listings/{id}/publish or
    POST /listings/{id}/repost to check whether the background task
    has completed, failed, or is still running.

    Possible values for `status`: pending, running, success, failed.
    """
    job = db.query(AutomationJob).filter(AutomationJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found.",
        )
    return job
