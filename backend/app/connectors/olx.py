from typing import Iterable, Mapping

from .base import BaseConnector


class OlxConnector(BaseConnector):
    name = "olx"

    def fetch_listings(self) -> Iterable[Mapping]:
        # Placeholder: implement OLX scraping with proper compliance.
        yield {
            "id": "olx-demo-1",
            "brand": "Fiat",
            "model": "Pulse",
            "year": 2022,
            "mileage_km": 15000,
            "price": 105000,
            "city": "Rio de Janeiro",
            "state": "RJ",
            "seller_type": "dealer",
            "photos": ["https://www.olx.com.br/photo.jpg"],
            "url": "https://www.olx.com.br/olx-demo-1",
        }

    def parse_listing(self, payload: Mapping) -> Mapping:
        return payload

    def normalize_fields(self, parsed: Mapping) -> Mapping:
        return {
            "external_id": parsed["id"],
            "brand": parsed.get("brand"),
            "model": parsed.get("model"),
            "trim": parsed.get("trim"),
            "year": parsed.get("year"),
            "mileage_km": parsed.get("mileage_km"),
            "price": parsed.get("price"),
            "city": parsed.get("city"),
            "state": parsed.get("state"),
            "photos": parsed.get("photos", []),
            "seller_type": parsed.get("seller_type"),
            "url": parsed.get("url"),
        }
