# Import all ORM models so SQLAlchemy's mapper registry is fully populated.
# Then call configure_mappers() to immediately resolve all string-based
# relationship() references (e.g. "User", "Listing", "AutomationJob").
# Any subsequent import of `app.models` is guaranteed to find a fully
# configured mapper registry — regardless of which submodule was imported first.

from app.models.user import User                         # noqa: F401
from app.models.listing import Listing, ListingStatus    # noqa: F401
from app.models.job import AutomationJob, JobStatus, JobType  # noqa: F401

from sqlalchemy.orm import configure_mappers
configure_mappers()

__all__ = [
    "User",
    "Listing",
    "ListingStatus",
    "AutomationJob",
    "JobStatus",
    "JobType",
]
