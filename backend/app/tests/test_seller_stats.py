from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.listing import NormalizedListing, Seller, SellerStats
from app.services.seller_stats import consolidate_seller_stats


def test_consolidate_seller_stats_generates_rankings():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seller = Seller(
            origin="mercadolivre",
            external_id="abc123",
            reputation_medal="gold",
            reputation_score=0.8,
            cancellations=2,
            completed_sales=100,
        )
        db.add(seller)
        db.flush()

        db.add_all(
            [
                NormalizedListing(
                    source_id=1,
                    external_id="l1",
                    brand="VW",
                    model="Nivus",
                    price_brl=110000,
                    final_price_brl=115000,
                    seller_id=seller.id,
                ),
                NormalizedListing(
                    source_id=1,
                    external_id="l2",
                    brand="VW",
                    model="Nivus",
                    price_brl=120000,
                    final_price_brl=125000,
                    seller_id=seller.id,
                ),
            ]
        )
        db.commit()

        consolidate_seller_stats(db)

        stats = db.execute(select(SellerStats).where(SellerStats.seller_id == seller.id)).scalar_one()
        assert stats.listings_count == 2
        assert stats.average_price_brl == 120000
        assert stats.problem_rate == 0.02
        assert stats.reliability_score > 0.8
