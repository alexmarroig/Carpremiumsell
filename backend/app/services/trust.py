from typing import Optional


class TrustSignals:
    def __init__(
        self,
        seller_type: Optional[str] = None,
        has_photos: bool = True,
        price_deviation: Optional[float] = None,
        listing_age_hours: Optional[int] = None,
    ) -> None:
        self.seller_type = seller_type
        self.has_photos = has_photos
        self.price_deviation = price_deviation
        self.listing_age_hours = listing_age_hours


def trust_badge(signals: TrustSignals) -> Optional[str]:
    score = 0
    if signals.seller_type == "dealer":
        score += 2
    if signals.has_photos:
        score += 1
    if signals.price_deviation is not None and signals.price_deviation < -0.2:
        score -= 1
    if signals.listing_age_hours is not None and signals.listing_age_hours < 6:
        score -= 1

    if score >= 3:
        return "Verified listing"
    if score >= 2:
        return "Selected by AXIS"
    return None
