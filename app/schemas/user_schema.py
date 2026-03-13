"""
Pydantic schemas for the User resource.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreateRequest(BaseModel):
    """Payload for POST /api/v1/users (registration)."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Plain-text password – hashed before storage")


class UserResponse(BaseModel):
    """Public user representation – never exposes password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    created_at: datetime
