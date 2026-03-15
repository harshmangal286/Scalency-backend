"""
AI Listing Generation Service.

Calls the OpenRouter API or Claude API (with fallback) to generate structured
listing data from a product image URL or plain text attributes.

Priority:
  1. Try OpenRouter API if OPENROUTER_API_KEY is configured
  2. Fall back to Claude API if OpenRouter fails or key is missing
  3. Raise error if both are unavailable

The primary function `generate_and_save_draft` also persists the result as a
draft Listing in the database, so the frontend can go straight to publish.
"""

import json
import logging
import uuid as uuid_module
from typing import Optional

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import (
    LOCALHOST_PREFIXES,
    MEDIA_TYPE_MAP,
    DEFAULT_MEDIA_TYPE,
    UPLOADS_DIR,
)
from app.models import Listing, ListingStatus    # package import triggers configure_mappers()
from app.schemas.listing_schema import AIGeneratedListing
from app.services.pricing_service import suggest_price

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """
You are an AI assistant specialized in generating marketplace listings for clothing resale platforms.

You will receive an image of a product.

Analyze the product carefully and extract as many attributes as possible.

Return the result in JSON format only.

The JSON must contain the following fields:

title
description
hashtags
brand
category
material
style
color
condition_estimate

Instructions:

- The title should be short and optimized for resale marketplaces.
- The description should sound natural and suitable for selling the product online.
- Hashtags must be relevant fashion keywords.
- Brand must be detected if visible.
- Category should be a clothing category (shirt, jacket, pants, etc).
- Material should be guessed if possible (cotton, denim, wool, etc).
- Style refers to fashion style (military, streetwear, vintage, casual, etc).
- Color should describe the main color of the product.
- Condition_estimate should be one of: new, like_new, good, used.

Return ONLY JSON in this format:

{
  "title": "",
  "description": "",
  "hashtags": [],
  "brand": "",
  "category": "",
  "material": "",
  "style": "",
  "color": "",
  "condition_estimate": ""
}
""".strip()


async def generate_and_save_draft(
    image_url: str,
    user_id: uuid_module.UUID,
    db: Session,
    stock: int = 1,
    additional_image_urls: list = None,
) -> AIGeneratedListing:
    """
    Main entry point for the /generate endpoint.

    1. Try OpenRouter with the image URL.
    2. If OpenRouter fails/unavailable, fall back to Claude API.
    3. Parse the structured response.
    4. Persist a draft Listing in the DB immediately.
    5. Return AIGeneratedListing (includes listing_id).

    Args:
        image_url: Publicly accessible product image URL (used for AI analysis).
        user_id:   UUID of the authenticated user who owns the listing.
        db:        SQLAlchemy session (injected by FastAPI's Depends).
        stock:     Initial quantity in stock (defaults to 1).
        additional_image_urls: List of additional product image URLs (optional).

    Raises:
        ValueError: On missing API keys or unparseable AI response.
        httpx.HTTPStatusError: On non-2xx responses from all AI services.
    """
    if additional_image_urls is None:
        additional_image_urls = []
    # Try OpenRouter first
    if settings.OPENROUTER_API_KEY:
        try:
            logger.info("Attempting to call OpenRouter API...")
            raw_content = await _call_openrouter(image_url)
            logger.info("OpenRouter call succeeded")
            generated = _parse_ai_response(raw_content)
        except Exception as exc:
            logger.warning(f"OpenRouter failed: {exc}. Falling back to Claude...")
            if settings.CLAUDE_API_KEY:
                try:
                    raw_content = await _call_claude(image_url)
                    logger.info("Claude call succeeded (fallback)")
                    generated = _parse_ai_response(raw_content)
                except Exception as exc2:
                    logger.error(f"Claude also failed: {exc2}")
                    raise ValueError(f"Both AI services failed. OpenRouter: {exc}. Claude: {exc2}") from exc2
            else:
                raise ValueError(f"OpenRouter failed and CLAUDE_API_KEY not configured: {exc}") from exc
    elif settings.CLAUDE_API_KEY:
        try:
            logger.info("OpenRouter not configured, using Claude API...")
            raw_content = await _call_claude(image_url)
            logger.info("Claude call succeeded")
            generated = _parse_ai_response(raw_content)
        except Exception as exc:
            logger.error(f"Claude API failed: {exc}")
            raise ValueError(f"Claude API failed: {exc}") from exc
    else:
        raise ValueError("Neither OPENROUTER_API_KEY nor CLAUDE_API_KEY is configured.")

    # Persist a draft listing immediately so the frontend gets a listing_id
    draft = Listing(
        user_id=user_id,
        title=generated["title"],
        description=generated["description"],
        brand=generated["brand"],
        category=generated["category"],
        material=generated["material"],
        style=generated["style"],
        color=generated["color"],
        condition=generated["condition_estimate"],  # map AI field → DB field
        hashtags=generated["hashtags"],
        image_urls=[image_url] + (additional_image_urls if additional_image_urls else []),
        stock=stock,
        status=ListingStatus.DRAFT,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    price_suggestion = suggest_price(
        generated["brand"],
        generated["category"],
        generated["condition_estimate"],
    )

    return AIGeneratedListing(
        listing_id=draft.id,
        title=generated["title"],
        description=generated["description"],
        hashtags=generated["hashtags"],
        brand=generated["brand"],
        category=generated["category"],
        material=generated["material"],
        style=generated["style"],
        color=generated["color"],
        condition_estimate=generated["condition_estimate"],
        image_urls=[image_url] + (additional_image_urls if additional_image_urls else []),
        stock=stock,
        price_suggestion=price_suggestion,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_localhost_url(url: str) -> bool:
    """Check if URL points to localhost."""
    return url.startswith(LOCALHOST_PREFIXES)


async def _get_image_as_base64(image_url: str) -> tuple[str, str]:
    """
    Convert image URL to base64 encoded string.

    If URL is localhost, reads file directly from disk.
    If URL is remote, downloads via httpx.

    Args:
        image_url: Image URL (localhost or remote)

    Returns:
        Tuple of (base64_string, media_type)
        Example: ("iVBORw0KGgo...", "image/jpeg")

    Raises:
        ValueError: If file not found or image cannot be read
        httpx.HTTPStatusError: If remote download fails
    """
    from pathlib import Path
    import base64

    # Check if it's a localhost URL
    if _is_localhost_url(image_url):
        # Extract filename from URL
        # Format: http://localhost:8000/api/v1/listings/uploads/{filename}
        filename = image_url.split("/uploads/")[-1]
        file_path = UPLOADS_DIR / filename

        # Security: prevent directory traversal
        if not file_path.is_relative_to(UPLOADS_DIR):
            raise ValueError("Invalid file path")

        # Use EAFP to avoid TOCTOU race condition
        try:
            with open(file_path, "rb") as f:
                image_data = f.read()
        except FileNotFoundError as exc:
            raise ValueError(f"Uploaded image file not found: {filename}") from exc
        except IOError as exc:
            raise ValueError(f"Failed to read image file: {exc}") from exc

        # Determine media type from file extension
        ext = file_path.suffix.lower()
        media_type = MEDIA_TYPE_MAP.get(ext, DEFAULT_MEDIA_TYPE)

        logger.info(f"Read local image from disk: {filename} ({media_type})")
    else:
        # Download remote image
        async with httpx.AsyncClient(timeout=30) as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            image_data = img_response.content

        # Determine media type from response headers or default
        media_type = img_response.headers.get("content-type", DEFAULT_MEDIA_TYPE)
        logger.info(f"Downloaded remote image: {image_url} ({media_type})")

    # Convert to base64
    base64_encoded = base64.standard_b64encode(image_data).decode("utf-8")
    return base64_encoded, media_type


async def _call_openrouter(image_url: str) -> str:
    """Call OpenRouter API and return raw content."""
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://scalency.local",  # Required by OpenRouter (generic domain)
        "X-Title": "Scalency",
    }

    # Check if localhost image - convert to base64
    if _is_localhost_url(image_url):
        logger.info("Detected localhost image URL, converting to base64...")
        base64_data, media_type = await _get_image_as_base64(image_url)
        # OpenRouter expects data: URI with embedded base64
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": f"data:{media_type};base64,{base64_data}",
            },
        }
    else:
        # Keep remote URLs as-is for efficiency
        image_content = {
            "type": "image_url",
            "image_url": {
                "url": image_url,
            },
        }

    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Generate a resale listing for the product shown in this image.",
                    },
                    image_content,
                ],
            },
        ],
        "temperature": 0.4,
        "max_tokens": 512,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )

        # Log detailed error for debugging
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"OpenRouter request failed with {response.status_code}: {error_detail}")
            logger.error(f"Request payload: {payload}")

        response.raise_for_status()

    data = response.json()
    return data["choices"][0]["message"]["content"]


async def _call_claude(image_url: str) -> str:
    """Call Claude API (Anthropic) and return raw content."""
    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Get image as base64 (handles both localhost and remote URLs)
    base64_data, media_type = await _get_image_as_base64(image_url)

    payload = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": 512,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": base64_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": f"{_SYSTEM_PROMPT}\n\nGenerate a resale listing for the product shown in this image.",
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.ANTHROPIC_BASE_URL}/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    return data["content"][0]["text"]


def _parse_ai_response(raw: str) -> dict:
    """
    Parse the AI's raw JSON string into a plain dict.
    Strips markdown fences if the model added them.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse AI response: %s", raw)
        raise ValueError(f"AI returned invalid JSON: {exc}") from exc

    return {
        "title": payload.get("title", ""),
        "description": payload.get("description", ""),
        "hashtags": payload.get("hashtags") or [],
        "brand": payload.get("brand") or None,
        "category": payload.get("category") or None,
        "material": payload.get("material") or None,
        "style": payload.get("style") or None,
        "color": payload.get("color") or None,
        "condition_estimate": payload.get("condition_estimate") or None,
    }


async def generate_listing_from_attributes(
    brand: Optional[str],
    category: Optional[str],
    condition: Optional[str],
    extra_notes: Optional[str] = None,
) -> dict:
    """
    Generate listing copy from text-only attributes (no image).
    Uses OpenRouter with fallback to Claude API.
    Returns the raw parsed dict; caller is responsible for persisting.
    """
    user_message = (
        f"Brand: {brand or 'Unknown'}\n"
        f"Category: {category or 'Unknown'}\n"
        f"Condition: {condition or 'Unknown'}\n"
    )
    if extra_notes:
        user_message += f"Additional notes: {extra_notes}\n"

    # Try OpenRouter first
    if settings.OPENROUTER_API_KEY:
        try:
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://scalency.local",  # Required by OpenRouter (generic domain)
                "X-Title": "Scalency",
            }

            payload = {
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.4,
                "max_tokens": 512,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            return _parse_ai_response(raw_content)
        except Exception as exc:
            logger.warning(f"OpenRouter failed in text generation: {exc}. Trying Claude...")
            if not settings.CLAUDE_API_KEY:
                raise

    # Fall back to Claude
    headers = {
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": 512,
        "messages": [
            {
                "role": "user",
                "content": f"{_SYSTEM_PROMPT}\n\n{user_message}",
            }
        ],
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.ANTHROPIC_BASE_URL}/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()

    data = response.json()
    raw_content = data["content"][0]["text"]
    return _parse_ai_response(raw_content)
