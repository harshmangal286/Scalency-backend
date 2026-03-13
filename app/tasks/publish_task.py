"""
Publish Task – transitions a listing from draft to published.

The task:
1. Loads the listing from the database.
2. Sets status = "published".
3. Records the job outcome in the AutomationJob row.
"""

import logging
import uuid

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import AutomationJob, JobStatus, Listing, ListingStatus  # triggers configure_mappers()
from app.tasks.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def publish_listing_task(self, listing_id: str, job_id: str) -> dict:
    """
    Celery task that publishes a listing.

    Args:
        listing_id: UUID string of the target listing.
        job_id:     UUID string of the associated AutomationJob row.

    Returns:
        Dict with the outcome.
    """
    db: Session = SessionLocal()
    try:
        job: AutomationJob = db.query(AutomationJob).filter(
            AutomationJob.id == uuid.UUID(job_id)
        ).first()

        listing: Listing = db.query(Listing).filter(
            Listing.id == uuid.UUID(listing_id)
        ).first()

        if not listing:
            _fail_job(db, job, f"Listing {listing_id} not found.")
            return {"status": "failed", "reason": "listing not found"}

        # Mark job as running
        if job:
            job.status = JobStatus.RUNNING
            job.attempts += 1
            db.commit()

        # Core business logic: publish the listing
        listing.status = ListingStatus.PUBLISHED
        db.commit()
        db.refresh(listing)

        # Mark job as succeeded
        if job:
            job.status = JobStatus.SUCCESS
            db.commit()

        logger.info("Listing %s published successfully.", listing_id)
        return {"status": "success", "listing_id": listing_id}

    except Exception as exc:
        db.rollback()
        logger.exception("Error publishing listing %s: %s", listing_id, exc)

        job = db.query(AutomationJob).filter(
            AutomationJob.id == uuid.UUID(job_id)
        ).first()
        _fail_job(db, job, str(exc))

        raise self.retry(exc=exc)

    finally:
        db.close()


def _fail_job(db: Session, job: AutomationJob | None, message: str) -> None:
    if job:
        job.status = JobStatus.FAILED
        job.error_message = message[:1000]  # guard against huge stack traces
        db.commit()
