import logging
from datetime import datetime
from typing import Optional

from redis import Redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.example_marketplace import ExampleMarketplaceConnector
from app.connectors.mercadolivre import MercadoLivreConnector
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.listing import ListingSource, MarketStats, NormalizedListing, RawListing
from app.services.normalization import normalize_listing_fields
from app.services.pricing import apply_markup, compute_regional_market_stats
from app.services.trust import TrustSignals, trust_badge

logger = logging.getLogger(__name__)


def ingest_source(source_name: str) -> None:
    connector = ExampleMarketplaceConnector()
    with SessionLocal() as db:
        source = db.execute(select(ListingSource).where(ListingSource.name == source_name)).scalars().first()
        if not source:
            source = ListingSource(name=source_name, base_url="https://example.com", enabled=True)
            db.add(source)
            db.commit()
            db.refresh(source)

        for payload in connector.fetch_listings():
            existing = db.execute(
                select(RawListing).where(
                    RawListing.source_id == source.id, RawListing.external_id == payload["id"]
                )
            ).scalars().first()
            if existing:
                existing.raw_payload = payload
                existing.fetched_at = datetime.utcnow()
            else:
                raw = RawListing(source_id=source.id, external_id=payload["id"], raw_payload=payload)
                db.add(raw)
        db.commit()
        logger.info("Ingested raw listings for %s", source_name)


def ingest_marketplace(source: str, region_key: str, query_text: Optional[str] = None, limit: int = 30) -> None:
    settings = get_settings()
    connector = MercadoLivreConnector(region_key=region_key, query_text=query_text or "", limit=limit)
    redis_conn = Redis.from_url(settings.redis_url)
    queue = Queue("ingestion", connection=redis_conn)

    with SessionLocal() as db:
        source_obj = db.execute(select(ListingSource).where(ListingSource.name == source)).scalars().first()
        if not source_obj:
            source_obj = ListingSource(
                name=source, base_url="https://carros.mercadolivre.com.br", enabled=True
            )
            db.add(source_obj)
            db.commit()
            db.refresh(source_obj)

        inserted = 0
        raw_ids: list[int] = []
        for payload in connector.fetch_listings():
            external_id = payload.get("external_id") or payload.get("id")
            if not external_id:
                continue
            existing = db.execute(
                select(RawListing).where(
                    RawListing.source_id == source_obj.id, RawListing.external_id == external_id
                )
            ).scalars().first()
            if existing:
                existing.raw_payload = payload
                existing.fetched_at = datetime.utcnow()
                raw_id = existing.id
            else:
                raw = RawListing(
                    source_id=source_obj.id, external_id=external_id, raw_payload=payload
                )
                db.add(raw)
                db.flush()
                raw_id = raw.id
                inserted += 1
            raw_ids.append(raw_id)
        db.commit()
        logger.info(
            "[mercadolivre] region=%s query=%s listings=%s inserted=%s",
            region_key,
            query_text,
            len(raw_ids),
            inserted,
        )

        for raw_id in raw_ids:
            queue.enqueue(normalize_raw_listing, raw_id)


def normalize_raw_listing(raw_id: int) -> None:
    with SessionLocal() as db:
        raw = db.get(RawListing, raw_id)
        if not raw:
            logger.warning("Raw listing %s not found", raw_id)
            return
        data = normalize_listing_fields(raw.raw_payload)
        external_id = data.get("external_id") or raw.external_id
        if not external_id:
            logger.warning("Raw listing %s missing external id", raw_id)
            return

        price = data.get("price")
        final_price = apply_markup(price or 0)
        existing = db.execute(
            select(NormalizedListing).where(
                NormalizedListing.source_id == raw.source_id,
                NormalizedListing.external_id == external_id,
            )
        ).scalars().first()

        if existing:
            normalized = existing
            normalized.brand = data.get("brand")
            normalized.model = data.get("model")
            normalized.trim = data.get("trim")
            normalized.year = data.get("year")
            normalized.mileage_km = data.get("mileage_km")
            normalized.price_brl = price
            normalized.supplier_price_brl = price
            normalized.final_price_brl = final_price
            normalized.city = data.get("city")
            normalized.state = data.get("state")
            normalized.photos = data.get("photos")
            normalized.url = data.get("url")
            normalized.seller_type = data.get("seller_type")
        else:
            normalized = NormalizedListing(
                source_id=raw.source_id,
                external_id=external_id,
                brand=data.get("brand"),
                model=data.get("model"),
                trim=data.get("trim"),
                year=data.get("year"),
                mileage_km=data.get("mileage_km"),
                price_brl=price,
                supplier_price_brl=price,
                final_price_brl=final_price,
                city=data.get("city"),
                state=data.get("state"),
                photos=data.get("photos"),
                url=data.get("url"),
                seller_type=data.get("seller_type"),
                status="active",
            )
            db.add(normalized)

        signals = TrustSignals(
            seller_type=normalized.seller_type,
            has_photos=bool(normalized.photos),
            price_deviation=None,
            listing_age_hours=None,
        )
        normalized.trust_badge = trust_badge(signals)
        if normalized.state and normalized.brand and normalized.model:
            stats = compute_regional_market_stats(
                db, region_key=normalized.state, brand=normalized.brand, model=normalized.model
            )
            if stats:
                existing_stats = db.execute(
                    select(MarketStats).where(
                        MarketStats.region_key == normalized.state,
                        MarketStats.brand == normalized.brand,
                        MarketStats.model == normalized.model,
                    )
                ).scalars().first()
                if existing_stats:
                    existing_stats.median_price = stats.median_price
                    existing_stats.p25 = stats.p25
                    existing_stats.p75 = stats.p75
                    existing_stats.updated_at = datetime.utcnow()
                else:
                    stats.updated_at = datetime.utcnow()
                    db.add(stats)
        db.commit()
        logger.info("Normalized listing %s", raw_id)


def recompute_market_stats(region_key: str, model_key: str) -> None:
    with SessionLocal() as db:
        stats = db.execute(
            select(MarketStats).where(
                MarketStats.region_key == region_key,
                MarketStats.model == model_key,
            )
        ).scalars().first()

        computed = compute_regional_market_stats(db, region_key=region_key, model=model_key)
        if not computed:
            logger.info("No prices found for %s in %s", model_key, region_key)
            return

        if not stats:
            stats = MarketStats(
                region_key=region_key, brand=model_key.split(" ")[0], model=model_key
            )
            db.add(stats)

        stats.median_price = computed.median_price
        stats.p25 = computed.p25
        stats.p75 = computed.p75
        stats.updated_at = datetime.utcnow()
        db.commit()
        logger.info("Recomputed market stats for %s", model_key)


def daily_opportunities(region_key: str) -> None:
    with SessionLocal() as db:
        listings = db.execute(select(NormalizedListing).where(NormalizedListing.state == region_key)).scalars().all()
        logger.info("Found %s listings for opportunities", len(listings))
