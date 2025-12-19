from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.listing import MarketStats, NormalizedListing
from app.schemas.listing import ListingOut, OpportunityResponse
from app.services.pricing import compute_opportunity_badge
from app.services.trust import TrustSignals, trust_badge

router = APIRouter(prefix="/v1", tags=["listings"])


@router.get("/opportunities", response_model=OpportunityResponse)
def opportunities(region: str, db: Session = Depends(get_db)) -> OpportunityResponse:
    stats = db.execute(select(MarketStats).where(MarketStats.region_key == region)).scalar_one_or_none()
    listings = db.execute(select(NormalizedListing).limit(20)).scalars().all()
    items = []
    for listing in listings:
        badge = compute_opportunity_badge(listing.final_price_brl or 0, stats.median_price if stats else None, stats.p25 if stats else None)
        badge = badge or trust_badge(TrustSignals(seller_type=listing.seller_type, has_photos=bool(listing.photos)))
        listing.badge = badge  # type: ignore[attr-defined]
        items.append(listing)
    return OpportunityResponse(items=items, count=len(items))


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> ListingOut:
    listing = db.get(NormalizedListing, listing_id)
    return listing
