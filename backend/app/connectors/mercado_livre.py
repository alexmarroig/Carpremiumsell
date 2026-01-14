import logging
from typing import Iterable, Mapping, Optional

import httpx

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class MercadoLivreConnector(BaseConnector):
    name = "mercado_livre"
    base_url = "https://api.mercadolibre.com"

    def __init__(self, region_key: str = "", query_text: str = "carros", limit: int = 20) -> None:
        self.region_key = region_key
        self.query_text = query_text
        self.limit = limit

    def fetch_listings(self) -> Iterable[Mapping]:
        params = {"q": self.query_text, "limit": self.limit}
        if self.region_key:
            params["state"] = self.region_key

        with httpx.Client(timeout=10) as client:
            response = client.get(f"{self.base_url}/sites/MLB/search", params=params)
            response.raise_for_status()
            results = response.json().get("results", [])

            for result in results:
                try:
                    yield self.parse_listing(result, client=client)
                except Exception:
                    logger.exception("Failed to parse Mercado Livre listing %s", result.get("id"))

    def parse_listing(self, payload: Mapping, client: Optional[httpx.Client] = None) -> Mapping:
        item_id = payload.get("id")
        if not item_id:
            raise ValueError("Missing listing id")

        created_client = False
        if client is None:
            client = httpx.Client(timeout=10)
            created_client = True

        try:
            item_data = self._fetch_json(client, f"/items/{item_id}")
            seller_id = item_data.get("seller_id")
            seller_data = self._fetch_seller_data(client, seller_id) if seller_id else {}
        finally:
            if created_client:
                client.close()

        pictures = item_data.get("pictures") or []
        attributes = item_data.get("attributes") or []
        attributes_map = {attr.get("id"): attr.get("value_name") for attr in attributes}

        price = item_data.get("price") or payload.get("price")
        brand = attributes_map.get("BRAND")
        model = attributes_map.get("MODEL")
        year = attributes_map.get("VEHICLE_YEAR") or attributes_map.get("YEAR")
        mileage = attributes_map.get("KILOMETERS") or attributes_map.get("MILEAGE")

        return {
            "id": item_id,
            "title": item_data.get("title") or payload.get("title"),
            "brand": brand,
            "model": model,
            "year": int(year) if year else None,
            "mileage_km": int(mileage) if mileage else None,
            "price": price,
            "city": (item_data.get("seller_address") or {}).get("city", {}).get("name"),
            "state": (item_data.get("seller_address") or {}).get("state", {}).get("id"),
            "seller_type": "dealer" if "car_dealer" in payload.get("tags", []) else "private",
            "photos": [pic.get("secure_url") or pic.get("url") for pic in pictures if pic.get("url")],
            "url": item_data.get("permalink") or payload.get("permalink"),
            "external_id": item_id,
            "seller_id": seller_id,
            "seller_reputation": self._build_seller_reputation(seller_data),
        }

    def normalize_fields(self, parsed: Mapping) -> Mapping:
        return {
            "external_id": parsed.get("external_id") or parsed.get("id"),
            "brand": parsed.get("brand"),
            "model": parsed.get("model"),
            "trim": parsed.get("trim"),
            "year": parsed.get("year"),
            "mileage_km": parsed.get("mileage_km"),
            "price": parsed.get("price"),
            "city": parsed.get("city"),
            "state": parsed.get("state"),
            "seller_type": parsed.get("seller_type"),
            "photos": parsed.get("photos", []),
            "url": parsed.get("url"),
            "seller_id": parsed.get("seller_id"),
            "seller_reputation": parsed.get("seller_reputation"),
        }

    def _fetch_json(self, client: httpx.Client, path: str) -> Mapping:
        response = client.get(f"{self.base_url}{path}")
        response.raise_for_status()
        return response.json()

    def _fetch_seller_data(self, client: httpx.Client, seller_id: Optional[str]) -> Mapping:
        if not seller_id:
            return {}
        try:
            return self._fetch_json(client, f"/users/{seller_id}")
        except httpx.HTTPError:
            logger.exception("Failed to fetch seller data for %s", seller_id)
            return {}

    def _build_seller_reputation(self, seller_data: Mapping) -> Mapping:
        rep = seller_data.get("seller_reputation", {}) if seller_data else {}
        metrics = rep.get("metrics", {}) if isinstance(rep, Mapping) else {}
        transactions = rep.get("transactions", {}) if isinstance(rep, Mapping) else {}
        ratings = transactions.get("ratings", {}) if isinstance(transactions, Mapping) else {}

        return {
            "level_id": rep.get("level_id") if isinstance(rep, Mapping) else None,
            "power_seller_status": rep.get("power_seller_status") if isinstance(rep, Mapping) else None,
            "cancellation_rate": (metrics.get("cancellations") or {}).get("rate") if isinstance(metrics, Mapping) else None,
            "claim_rate": (metrics.get("claims") or {}).get("rate") if isinstance(metrics, Mapping) else None,
            "negative_rating": ratings.get("negative") if isinstance(ratings, Mapping) else None,
            "neutral_rating": ratings.get("neutral") if isinstance(ratings, Mapping) else None,
            "positive_rating": ratings.get("positive") if isinstance(ratings, Mapping) else None,
            "completed_sales": (transactions.get("completed") if isinstance(transactions, Mapping) else None),
            "total_sales": (transactions.get("total") if isinstance(transactions, Mapping) else None),
            "canceled_sales": (transactions.get("canceled") if isinstance(transactions, Mapping) else None),
        }
