"""
Health-check endpoint.
Used by load balancers and container orchestration systems to verify
the service is alive and can reach the database.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health_check(db: Session = Depends(get_db)) -> dict:
    """
    Returns the service status and a quick database connectivity probe.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        db_status = f"error: {exc}"

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database": db_status,
    }
