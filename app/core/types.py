"""
Database-agnostic column types that work with both PostgreSQL and SQLite.
"""

import uuid as uuid_module
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy import JSON
import json

from app.core.config import settings


def is_sqlite():
    """Check if using SQLite database."""
    return "sqlite" in settings.DATABASE_URL.lower()


class UUID(TypeDecorator):
    """
    Platform-independent UUID type.

    Uses BINARY(16) on SQLite and UUID on PostgreSQL.
    Stores as string internally for portability.
    """
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if "postgresql" in dialect.name:
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if "postgresql" in dialect.name:
            return value
        if isinstance(value, uuid_module.UUID):
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid_module.UUID):
            return value
        return uuid_module.UUID(value)


class ARRAY(TypeDecorator):
    """
    Platform-independent ARRAY type.

    Uses JSON on SQLite and ARRAY on PostgreSQL.
    """
    impl = JSON
    cache_ok = True

    def __init__(self, item_type, *args, **kwargs):
        self.item_type = item_type
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if "postgresql" in dialect.name:
            return dialect.type_descriptor(PG_ARRAY(self.item_type))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if "postgresql" in dialect.name:
            return value
        return value if isinstance(value, (list, dict)) else []

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return value if isinstance(value, list) else []
