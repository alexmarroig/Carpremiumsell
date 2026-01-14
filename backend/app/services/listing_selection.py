from typing import Optional

from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from app.models.listing import NormalizedListing


DEFAULT_MIN_REPUTATION = 0.7


def select_cheapest_with_reputation(
    db: Session, min_reputation: float = DEFAULT_MIN_REPUTATION
) -> Optional[NormalizedListing]:
    stmt = (
        select(NormalizedListing)
        .where(NormalizedListing.seller_reputation >= min_reputation)
        .order_by(asc(NormalizedListing.price_brl), asc(NormalizedListing.id))
    )
    return db.execute(stmt).scalars().first()

