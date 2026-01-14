import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.base import BaseConnector
from app.connectors.example_marketplace import ExampleMarketplaceConnector
from app.connectors.mercadolivre import MercadoLivreConnector
from app.connectors.olx import OlxConnector
from app.db.session import SessionLocal
from app.models.listing import ListingSource, MarketStats, NormalizedListing, RawListing
from app.services.normalization import normalize_listing_fields
from app.services.pricing import apply_markup, compute_regional_market_stats

logger = logging.getLogger(__name__)


@dataclass
class ConnectorConfig:
    base_url: str
    factory: Callable[..., BaseConnector]


def _example_factory(**_: Any) -> BaseConnector:
    return ExampleMarketplaceConnector()


def _mercado_livre_factory(region_key: str = "", query_text: str = "", limit: int = 30, **_: Any) -> BaseConnector:
    return MercadoLivreConnector(region_key=region_key, query_text=query_text, limit=limit)


def _olx_factory(**_: Any) -> BaseConnector:
    return OlxConnector()


CONNECTOR_REGISTRY: dict[str, ConnectorConfig] = {
    "mercado_livre": ConnectorConfig(
        base_url="https://carros.mercadolivre.com.br", factory=_mercado_livre_factory
    ),
    "mercadolivre": ConnectorConfig(
        base_url="https://carros.mercadolivre.com.br", factory=_mercado_livre_factory
    ),
    "olx": ConnectorConfig(base_url="https://www.olx.com.br", factory=_olx_factory),
}

DEFAULT_CONNECTOR = ConnectorConfig(base_url="https://example.com", factory=_example_factory)


def get_connector_config(source_name: str) -> ConnectorConfig:
    return CONNECTOR_REGISTRY.get(source_name, DEFAULT_CONNECTOR)


def ingest_source(source_name: str, region_key: str = "", query_text: str | None = None, limit: int = 30) -> None:
    config = get_connector_config(source_name)
    connector = config.factory(region_key=region_key, query_text=query_text or "", limit=limit)
    with SessionLocal() as db:
        source = db.execute(select(ListingSource).where(ListingSource.name == source_name)).scalars().first()
        if not source:
            source = ListingSource(name=source_name, base_url=config.base_url, enabled=True)
            db.add(source)
            db.commit()
            db.refresh(source)
        elif source.base_url != config.base_url:
            source.base_url = config.base_url
            db.add(source)
            db.commit()
            db.refresh(source)

        for payload in connector.fetch_listings():
            raw = RawListing(source_id=source.id, external_id=payload["id"], raw_payload=payload)
            db.add(raw)
        db.commit()
        logger.info("Ingested raw listings for %s", source_name)


def ingest_marketplace(source_name: str, region_key: str, query_text: str = "", limit: int = 30) -> None:
    ingest_source(source_name=source_name, region_key=region_key, query_text=query_text, limit=limit)


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
