"""
Listing model – represents a resale product listing.
A listing moves through statuses: draft → published → sold / archived.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.types import UUID, ARRAY


class ListingStatus:
    DRAFT = "draft"
    PUBLISHED = "published"
    SOLD = "sold"
    ARCHIVED = "archived"
    REPOSTED = "reposted"


class Listing(Base):
    __tablename__ = "listings"

    id: uuid.UUID = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    user_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Core product details
    title: str = Column(String(255), nullable=False)
    description: str = Column(Text, nullable=True)
    brand: str = Column(String(100), nullable=True)
    category: str = Column(String(100), nullable=True)
    size: str = Column(String(50), nullable=True)
    condition: str = Column(String(50), nullable=True)

    # AI-extracted extended attributes
    material: str = Column(String(100), nullable=True)
    style: str = Column(String(100), nullable=True)
    color: str = Column(String(100), nullable=True)
    hashtags: list = Column(ARRAY(String), nullable=True, default=list)

    # Image storage – multiple images per listing
    image_urls: list = Column(ARRAY(String), nullable=True, default=list)

    # Pricing & stock
    price: float = Column(Numeric(10, 2), nullable=True)
    stock: int = Column(Integer, default=1, nullable=False)

    # Workflow state
    status: str = Column(String(50), default=ListingStatus.DRAFT, nullable=False)

    # Optional reference to the listing this was cloned from (repost flow)
    parent_listing_id: uuid.UUID = Column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: datetime = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="listings")
    jobs = relationship("AutomationJob", back_populates="listing", lazy="dynamic", cascade="all, delete")

    def __repr__(self) -> str:
        return f"<Listing id={self.id} title={self.title!r} status={self.status}>"
