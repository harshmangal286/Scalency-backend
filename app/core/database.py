"""
SQLAlchemy engine, session factory, and declarative base.
Import `SessionLocal` for dependency injection and `Base` for model definitions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

"""
SQLAlchemy engine, session factory, and declarative base.
Import `SessionLocal` for dependency injection and `Base` for model definitions.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings

# Connection pool tuned for the database type
if "sqlite" in settings.DATABASE_URL.lower():
    # SQLite doesn't need connection pooling
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL with connection pooling
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,       # detect stale connections automatically
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that yields a DB session and guarantees cleanup.
    Usage:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """Create all tables that are registered on Base.metadata."""
    # Import models so SQLAlchemy registers them before creating tables
    from app.models import user, listing, job  # noqa: F401

    Base.metadata.create_all(bind=engine, checkfirst=True)
