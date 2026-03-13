"""Shared constants for Scalency backend."""

from pathlib import Path

# Image uploads configuration
UPLOADS_DIR = Path("/tmp/scalency_uploads")
UPLOADS_URL_PATH = "/uploads/"

# Image handling
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MEDIA_TYPE_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}
DEFAULT_MEDIA_TYPE = "image/jpeg"

# Localhost detection
LOCALHOST_PREFIXES = ("http://localhost:", "http://127.0.0.1:")
