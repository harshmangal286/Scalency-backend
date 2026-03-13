"""
AI Listing Generation Service.

Calls the OpenRouter API (OpenAI-compatible endpoint) to generate structured
listing data from a product image URL or plain text attributes.

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
) -> AIGeneratedListing:
    """
    Main entry point for the /generate endpoint.

    1. Calls OpenRouter with the image URL.
    2. Parses the structured response.
    3. Persists a draft Listing in the DB immediately.
    4. Returns AIGeneratedListing (includes listing_id).

    Args:
        image_url: Publicly accessible product image URL.
        user_id:   UUID of the authenticated user who owns the listing.
        db:        SQLAlchemy session (injected by FastAPI's Depends).

    Raises:
        ValueError: On missing API key or unparseable AI response.
        httpx.HTTPStatusError: On non-2xx responses from OpenRouter.
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
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
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url},
                    },
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
        response.raise_for_status()

    data = response.json()
    raw_content: str = data["choices"][0]["message"]["content"]

    generated = _parse_ai_response(raw_content)

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
        image_urls=[image_url],
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
        image_urls=[image_url],
        price_suggestion=price_suggestion,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

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
    Useful as a fallback when no image is available.
    Returns the raw parsed dict; caller is responsible for persisting.
    """
    if not settings.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    user_message = (
        f"Brand: {brand or 'Unknown'}\n"
        f"Category: {category or 'Unknown'}\n"
        f"Condition: {condition or 'Unknown'}\n"
    )
    if extra_notes:
        user_message += f"Additional notes: {extra_notes}\n"

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
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
    raw_content: str = data["choices"][0]["message"]["content"]
    return _parse_ai_response(raw_content)
