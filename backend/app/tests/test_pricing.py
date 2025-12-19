from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.listing import NormalizedListing
from app.services.pricing import (
    apply_markup,
    compute_opportunity_badge,
    compute_regional_market_stats,
    detect_opportunity,
)


def test_apply_markup_mid_category():
    assert apply_markup(100000, "mid") == 108500.0


def test_compute_opportunity_badge():
    badge = compute_opportunity_badge(90000, median=100000, p25=95000)
    assert badge == "Selected by AXIS"


def test_compute_regional_market_stats_and_opportunity():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                NormalizedListing(
                    source_id=1,
                    external_id="1",
                    brand="Honda",
                    model="Civic",
                    price_brl=100000,
                    state="SP",
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="2",
                    brand="Honda",
                    model="Civic",
                    price_brl=90000,
                    state="SP",
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="3",
                    brand="Honda",
                    model="Civic",
                    price_brl=110000,
                    state="SP",
                ),
            ]
        )
        db.commit()

        stats = compute_regional_market_stats(db, region_key="SP", brand="Honda", model="Civic")
        assert stats is not None
        assert stats.median_price == 100000
        assert stats.p25 == 90000
        assert stats.p75 == 110000

        badge = detect_opportunity(price_brl=85000, market=stats)
        assert badge == "Selected by AXIS"
