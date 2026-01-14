import statistics
from typing import Iterable, Literal, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.listing import MarketStats, NormalizedListing


Category = Literal["popular", "mid", "premium", "rare"]


CATEGORY_MARKUP = {
    "popular": (0.05, 0.07),
    "mid": (0.07, 0.10),
    "premium": (0.07, 0.10),
    "rare": (0.10, 0.15),
}


def apply_markup(listing_price: float, category: Category = "mid") -> float:
    low, high = CATEGORY_MARKUP.get(category, CATEGORY_MARKUP["mid"])
    midpoint = (low + high) / 2
    return round(listing_price * (1 + midpoint), 2)


def _percentile(values: Sequence[float], percentile: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    rank = max(1, int(len(values) * percentile + 0.9999)) - 1
    return float(values[min(rank, len(values) - 1)])


def compute_regional_market_stats(
    db: Session, region_key: str, brand: Optional[str] = None, model: Optional[str] = None
) -> Optional[MarketStats]:
    stmt = select(NormalizedListing.price_brl).where(NormalizedListing.state == region_key)
    if brand:
        stmt = stmt.where(NormalizedListing.brand == brand)
    if model:
        stmt = stmt.where(NormalizedListing.model == model)

    prices: Iterable[float] = [p[0] for p in db.execute(stmt) if p[0] is not None]
    prices = sorted(prices)
    if not prices:
        return None

    median_price = statistics.median(prices)
    p25 = _percentile(prices, 0.25)
    p75 = _percentile(prices, 0.75)

    stats = MarketStats(
        region_key=region_key,
        brand=brand or "*",
        model=model or "*",
        median_price=median_price,
        p25=p25,
        p75=p75,
    )
    return stats


def compute_opportunity_badge(price_brl: float, median: Optional[float], p25: Optional[float]) -> Optional[str]:
    if median is None or p25 is None or price_brl is None:
        return None
    discount_vs_median = (median - price_brl) / median if median else 0
    if price_brl <= p25 or discount_vs_median >= 0.1:
        return "Selected by AXIS"
    return None


def detect_opportunity(price_brl: float, market: Optional[MarketStats]) -> Optional[str]:
    if not market:
        return None
    return compute_opportunity_badge(price_brl, median=market.median_price, p25=market.p25)
