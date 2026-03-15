"""
AutomationJob model – tracks background Celery jobs tied to a listing.
Allows monitoring, error surfacing, and retry logic.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import UUID


class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class JobType:
    PUBLISH = "publish"
    REPOST = "repost"


class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    listing_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_type: str = Column(String(50), nullable=False)   # publish | repost
    status: str = Column(String(50), default=JobStatus.PENDING, nullable=False)
    attempts: int = Column(Integer, default=0, nullable=False)
    error_message: str = Column(Text, nullable=True)

    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    listing = relationship("Listing", back_populates="jobs")

    def __repr__(self) -> str:
        return (
            f"<AutomationJob id={self.id} type={self.job_type} status={self.status}>"
        )
