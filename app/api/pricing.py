"""
Pricing API – price suggestion endpoint.
"""

from fastapi import APIRouter

from app.schemas.listing_schema import PriceSuggestionRequest, PriceSuggestionResponse
from app.services.pricing_service import suggest_price

router = APIRouter(prefix="/api/v1/pricing", tags=["pricing"])


@router.post(
    "/suggest",
    response_model=PriceSuggestionResponse,
    summary="Get an AI-assisted price suggestion",
)
def get_price_suggestion(body: PriceSuggestionRequest) -> PriceSuggestionResponse:
    """
    Returns a recommended price and a min/max range based on brand,
    category, and item condition.
    """
    return suggest_price(
        brand=body.brand,
        category=body.category,
        condition=body.condition,
    )
