from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.listing import MarketStats, NormalizedListing
from app.schemas.listing import ListingOut, OpportunityResponse, SellerStatsOut
from app.services.pricing import compute_opportunity_badge, compute_regional_market_stats
from app.services.seller_stats import top_trusted_sellers
from app.services.trust import TrustSignals, trust_badge

router = APIRouter(prefix="/v1", tags=["listings"])


@router.get("/opportunities", response_model=OpportunityResponse)
def opportunities(region: str, db: Session = Depends(get_db)) -> OpportunityResponse:
    stats = db.execute(select(MarketStats).where(MarketStats.region_key == region)).scalar_one_or_none()
    if not stats:
        stats = compute_regional_market_stats(db, region_key=region)
    listings = db.execute(select(NormalizedListing).limit(20)).scalars().all()
    items = []
    for listing in listings:
        badge = compute_opportunity_badge(listing.final_price_brl or 0, stats.median_price if stats else None, stats.p25 if stats else None)
        badge = badge or trust_badge(TrustSignals(seller_type=listing.seller_type, has_photos=bool(listing.photos)))
        listing.badge = badge  # type: ignore[attr-defined]
        items.append(listing)
    return OpportunityResponse(items=items, count=len(items))


@router.get("/trusted-sellers", response_model=list[SellerStatsOut])
def trusted_sellers(
    limit: int = Query(10, ge=1, le=50),
    origin: str | None = None,
    db: Session = Depends(get_db),
) -> list[SellerStatsOut]:
    stats = top_trusted_sellers(db, limit=limit, origin=origin)
    response: list[SellerStatsOut] = []
    for stat in stats:
        seller = getattr(stat, "seller", None)
        response.append(
            SellerStatsOut(
                seller_id=stat.seller_id,
                origin=seller.origin if seller else "",
                reputation_medal=seller.reputation_medal if seller else None,
                reputation_score=seller.reputation_score if seller else None,
                cancellations=seller.cancellations if seller else None,
                response_time_hours=seller.response_time_hours if seller else None,
                completed_sales=seller.completed_sales if seller else stat.completed_sales,
                average_price_brl=stat.average_price_brl,
                listings_count=stat.listings_count,
                problem_rate=stat.problem_rate,
                reliability_score=stat.reliability_score,
            )
        )
    return response


@router.get("/listings/{listing_id}", response_model=ListingOut)
def get_listing(listing_id: int, db: Session = Depends(get_db)) -> ListingOut:
    listing = db.get(NormalizedListing, listing_id)
    return listing
