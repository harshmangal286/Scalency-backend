"""
Users API – registration and lookup.

This is intentionally minimal: no JWT auth, no login endpoint.
Its purpose is to let you create a real user_id for testing and
for the frontend to register users before creating listings.
"""

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.user_schema import UserCreateRequest, UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])

# bcrypt_sha256 pre-hashes the password with SHA-256 before bcrypt,
# removing bcrypt's 72-character truncation limit while keeping the same
# work-factor security. Fully supported by passlib >= 1.7.
_pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=UserResponse,
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Creates a new user with a bcrypt_sha256-hashed password.
    Returns the user record including the `id` needed for listing endpoints.
    """
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{body.email}' already exists.",
        )

    user = User(
        email=body.email,
        password_hash=_pwd_context.hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("New user registered: %s (id=%s)", user.email, user.id)
    return user


# ---------------------------------------------------------------------------
# Get by ID
# ---------------------------------------------------------------------------

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Fetch a user by ID",
)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Returns the user record for the given UUID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found.",
        )
    return user
