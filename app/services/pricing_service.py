"""
Price Suggestion Service.

Uses rule-based logic to derive a recommended price range from brand,
category, and condition.  Can be replaced with a real ML model or market-data
API without changing the public interface.
"""

import logging
from typing import Optional

from app.schemas.listing_schema import PriceSuggestionResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Base prices by category (EUR)
_CATEGORY_BASE_PRICE: dict[str, float] = {
    "electronics": 80.0,
    "phones": 120.0,
    "laptops": 250.0,
    "clothing": 25.0,
    "shoes": 40.0,
    "bags": 50.0,
    "watches": 80.0,
    "jewellery": 30.0,
    "books": 8.0,
    "toys": 15.0,
    "furniture": 60.0,
    "sports": 35.0,
    "default": 20.0,
}

# Brand multipliers (premium brands command higher prices)
_BRAND_MULTIPLIER: dict[str, float] = {
    # Luxury
    "louis vuitton": 8.0,
    "chanel": 7.5,
    "gucci": 6.0,
    "prada": 5.5,
    "hermes": 9.0,
    "rolex": 12.0,
    # Mid-range designer
    "michael kors": 2.5,
    "tommy hilfiger": 2.0,
    "ralph lauren": 2.2,
    "levis": 1.8,
    "calvin klein": 2.0,
    # Tech
    "apple": 4.0,
    "samsung": 2.5,
    "sony": 2.0,
    "nike": 2.0,
    "adidas": 1.8,
    "default": 1.0,
}

# Condition multipliers
_CONDITION_MULTIPLIER: dict[str, float] = {
    "new": 1.0,
    "like_new": 0.80,
    "good": 0.60,
    "fair": 0.40,
    "poor": 0.20,
}

# Price spread (min / max relative to recommended)
_SPREAD_FACTOR = 0.20  # ±20 %


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def suggest_price(
    brand: Optional[str],
    category: Optional[str],
    condition: Optional[str],
) -> PriceSuggestionResponse:
    """
    Return a recommended price and min/max range.

    Args:
        brand:     Product brand (case-insensitive).
        category:  Product category (case-insensitive).
        condition: Item condition string.

    Returns:
        PriceSuggestionResponse with recommended_price, min_price, max_price.
    """
    # Normalise inputs
    brand_key = (brand or "").strip().lower()
    category_key = (category or "").strip().lower()
    condition_key = (condition or "").strip().lower()

    # Resolve base price
    base_price = _CATEGORY_BASE_PRICE.get(category_key, _CATEGORY_BASE_PRICE["default"])

    # Resolve brand multiplier (exact match first, then substring scan)
    brand_mult = _BRAND_MULTIPLIER.get(brand_key)
    if brand_mult is None:
        brand_mult = next(
            (v for k, v in _BRAND_MULTIPLIER.items() if k in brand_key),
            _BRAND_MULTIPLIER["default"],
        )

    # Resolve condition multiplier
    condition_mult = _CONDITION_MULTIPLIER.get(condition_key, 0.5)

    recommended = round(base_price * brand_mult * condition_mult, 2)
    min_price = round(recommended * (1 - _SPREAD_FACTOR), 2)
    max_price = round(recommended * (1 + _SPREAD_FACTOR), 2)

    logger.debug(
        "Price suggestion: base=%.2f brand_mult=%.2f condition_mult=%.2f → %.2f",
        base_price,
        brand_mult,
        condition_mult,
        recommended,
    )

    return PriceSuggestionResponse(
        recommended_price=recommended,
        min_price=min_price,
        max_price=max_price,
    )
