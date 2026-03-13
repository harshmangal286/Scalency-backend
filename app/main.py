"""
Application entrypoint.

Table creation / migrations are intentionally NOT run here.
They are handled by entrypoint.sh before Uvicorn starts, so that DDL
executes exactly once regardless of how many Uvicorn worker processes
are spawned.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import health, jobs, listings, pricing, users

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description=(
            "Scalency – AI-assisted resale marketplace backend. "
            "Automates listing creation, pricing, publishing, and reposting."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS – tighten origins for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(users.router)
    app.include_router(listings.router)
    app.include_router(pricing.router)
    app.include_router(jobs.router)

    return app


app = create_app()
