from statistics import mean
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import NormalizedListing, Seller, SellerStats


def _compute_reliability_score(stats: SellerStats, seller: Seller) -> float:
    base = seller.reputation_score or 0
    medal_bonus = {
        "gold": 0.15,
        "silver": 0.1,
        "bronze": 0.05,
    }.get((seller.reputation_medal or "").lower(), 0)
    penalty = stats.problem_rate or 0
    activity_bonus = min((stats.completed_sales or 0) / 1000, 0.2)
    return max(0.0, min(1.0, base + medal_bonus + activity_bonus - penalty))


def consolidate_seller_stats(db: Session) -> None:
    sellers: Iterable[Seller] = db.execute(select(Seller)).scalars().all()
    for seller in sellers:
        listings = db.execute(
            select(NormalizedListing).where(NormalizedListing.seller_id == seller.id)
        ).scalars().all()
        if not listings:
            continue

        price_points = [
            listing.final_price_brl or listing.price_brl
            for listing in listings
            if listing.final_price_brl or listing.price_brl
        ]

        stats = db.execute(
            select(SellerStats).where(SellerStats.seller_id == seller.id)
        ).scalars().first()
        if not stats:
            stats = SellerStats(seller_id=seller.id)
            db.add(stats)

        stats.listings_count = len(listings)
        stats.average_price_brl = mean(price_points) if price_points else None
        stats.completed_sales = seller.completed_sales
        stats.problem_rate = (seller.cancellations or 0) / max(
            (seller.completed_sales or 1), 1
        )
        stats.reliability_score = _compute_reliability_score(stats, seller)
    db.commit()


def top_trusted_sellers(db: Session, limit: int = 10, origin: Optional[str] = None):
    stmt = select(SellerStats).order_by(SellerStats.reliability_score.desc()).limit(limit)
    if origin:
        stmt = stmt.join(Seller).where(Seller.origin == origin)
    return db.execute(stmt).scalars().all()
