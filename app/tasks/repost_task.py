"""
Repost Task – clones an existing listing and republishes the clone.

The task:
1. Loads the source listing.
2. Creates a new Listing with status = "draft", pointing back to the original
   via parent_listing_id.
3. Immediately triggers publish_listing_task for the new listing.
4. Records the job outcome.
"""

import logging
import uuid as uuid_module
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import AutomationJob, JobStatus, JobType, Listing, ListingStatus  # triggers configure_mappers()
from app.tasks.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def repost_listing_task(self, listing_id: str, job_id: str, stock: int = None) -> dict:
    """
    Celery task that clones a listing and republishes it.

    Args:
        listing_id: UUID string of the source listing to clone.
        job_id:     UUID string of the AutomationJob tracking this repost.
        stock:      Optional stock quantity for the reposted listing (defaults to source stock).

    Returns:
        Dict with the outcome and the new listing id.
    """
    db: Session = SessionLocal()
    try:
        job: AutomationJob = db.query(AutomationJob).filter(
            AutomationJob.id == uuid_module.UUID(job_id)
        ).first()

        source: Listing = db.query(Listing).filter(
            Listing.id == uuid_module.UUID(listing_id)
        ).first()

        if not source:
            _fail_job(db, job, f"Source listing {listing_id} not found.")
            return {"status": "failed", "reason": "listing not found"}

        # Mark job as running
        if job:
            job.status = JobStatus.RUNNING
            job.attempts += 1
            db.commit()

        # Clone the listing – copy all product attributes including AI fields
        new_listing = Listing(
            user_id=source.user_id,
            title=source.title,
            description=source.description,
            brand=source.brand,
            category=source.category,
            size=source.size,
            condition=source.condition,
            material=source.material,
            style=source.style,
            color=source.color,
            hashtags=list(source.hashtags) if source.hashtags else [],
            image_urls=list(source.image_urls) if source.image_urls else [],
            price=source.price,
            stock=stock if stock is not None else source.stock,
            status=ListingStatus.DRAFT,
            parent_listing_id=source.id,
        )
        db.add(new_listing)
        db.flush()  # assigns new_listing.id

        # Create a publish job for the clone
        publish_job = AutomationJob(
            listing_id=new_listing.id,
            job_type=JobType.PUBLISH,
            status=JobStatus.PENDING,
        )
        db.add(publish_job)
        db.commit()
        db.refresh(new_listing)
        db.refresh(publish_job)

        # Queue the publish task for the new clone
        from app.tasks.publish_task import publish_listing_task  # avoid circular import

        publish_listing_task.delay(str(new_listing.id), str(publish_job.id))

        # Mark the repost job succeeded
        if job:
            job.status = JobStatus.SUCCESS
            db.commit()

        logger.info(
            "Listing %s reposted as new listing %s.",
            listing_id,
            str(new_listing.id),
        )
        return {
            "status": "success",
            "source_listing_id": listing_id,
            "new_listing_id": str(new_listing.id),
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Error reposting listing %s: %s", listing_id, exc)

        job = db.query(AutomationJob).filter(
            AutomationJob.id == uuid_module.UUID(job_id)
        ).first()
        _fail_job(db, job, str(exc))

        raise self.retry(exc=exc)

    finally:
        db.close()


def _fail_job(db: Session, job: AutomationJob | None, message: str) -> None:
    if job:
        job.status = JobStatus.FAILED
        job.error_message = message[:1000]
        db.commit()
