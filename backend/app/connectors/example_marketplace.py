from typing import Iterable, Mapping

from .base import BaseConnector


class ExampleMarketplaceConnector(BaseConnector):
    name = "example_marketplace"

    def fetch_listings(self) -> Iterable[Mapping]:
        # Placeholder: implement Playwright session honoring robots.txt and ToS.
        # This stub yields synthetic data for local development only.
        yield {
            "id": "demo-1",
            "brand": "VW",
            "model": "T-Cross",
            "year": 2021,
            "mileage_km": 25000,
            "price": 120000,
            "city": "São Paulo",
            "state": "SP",
            "seller_type": "dealer",
            "seller_id": "demo_seller",
            "seller_origin": "example_marketplace",
            "seller_medal": "gold",
            "seller_score": 0.92,
            "seller_cancellations": 1,
            "seller_response_time_hours": 2.5,
            "seller_completed_sales": 320,
            "photos": ["https://example.com/photo.jpg"],
            "url": "https://example.com/listing/demo-1",
        }

    def parse_listing(self, payload: Mapping) -> Mapping:
        # In a real connector, parse HTML/JSON here.
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
            "seller_id": parsed.get("seller_id"),
            "seller_origin": parsed.get("seller_origin"),
            "seller_medal": parsed.get("seller_medal"),
            "seller_score": parsed.get("seller_score"),
            "seller_cancellations": parsed.get("seller_cancellations"),
            "seller_response_time_hours": parsed.get("seller_response_time_hours"),
            "seller_completed_sales": parsed.get("seller_completed_sales"),
            "url": parsed.get("url"),
        }
