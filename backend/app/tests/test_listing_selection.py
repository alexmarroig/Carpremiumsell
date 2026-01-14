from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.listing import NormalizedListing
from app.services.listing_selection import select_cheapest_with_reputation


def test_select_listing_filters_by_reputation_and_price():
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
                    price_brl=90000,
                    seller_reputation=0.6,
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="2",
                    brand="Honda",
                    model="Civic",
                    price_brl=120000,
                    seller_reputation=0.85,
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="3",
                    brand="Honda",
                    model="Civic",
                    price_brl=100000,
                    seller_reputation=0.9,
                ),
            ]
        )
        db.commit()

        listing = select_cheapest_with_reputation(db, min_reputation=0.8)

        assert listing is not None
        assert listing.external_id == "3"
        assert listing.price_brl == 100000


def test_select_listing_handles_price_ties():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add_all(
            [
                NormalizedListing(
                    source_id=1,
                    external_id="A",
                    brand="Ford",
                    model="Fiesta",
                    price_brl=80000,
                    seller_reputation=0.95,
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="B",
                    brand="Ford",
                    model="Fiesta",
                    price_brl=80000,
                    seller_reputation=0.9,
                ),
            ]
        )
        db.commit()

        listing = select_cheapest_with_reputation(db, min_reputation=0.8)

        assert listing is not None
        assert listing.external_id == "A"
