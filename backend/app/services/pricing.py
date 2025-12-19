from typing import Literal, Optional


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


def compute_opportunity_badge(price_brl: float, median: Optional[float], p25: Optional[float]) -> Optional[str]:
    if median is None or p25 is None:
        return None
    discount_vs_median = (median - price_brl) / median if median else 0
    if price_brl <= p25 or discount_vs_median >= 0.1:
        return "Selected by AXIS"
    return None
