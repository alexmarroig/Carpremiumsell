from typing import Dict, Optional


COMMON_BRANDS = {
    "vw": "Volkswagen",
    "gm": "Chevrolet",
    "chevy": "Chevrolet",
}


def normalize_brand(raw_brand: Optional[str]) -> Optional[str]:
    if not raw_brand:
        return None
    key = raw_brand.strip().lower()
    return COMMON_BRANDS.get(key, raw_brand.title())


def normalize_listing_fields(raw: Dict) -> Dict:
    brand = normalize_brand(raw.get("brand"))
    model = raw.get("model")
    return {
        "external_id": raw.get("id") or raw.get("external_id"),
        "brand": brand,
        "model": model.title() if isinstance(model, str) else model,
        "trim": raw.get("trim"),
        "year": int(raw["year"]) if raw.get("year") else None,
        "mileage_km": raw.get("mileage_km"),
        "price": float(raw.get("price")) if raw.get("price") else None,
        "city": raw.get("city"),
        "state": raw.get("state"),
        "seller_type": raw.get("seller_type", "private"),
        "seller_id": raw.get("seller_id"),
        "seller_origin": raw.get("seller_origin"),
        "seller_medal": raw.get("seller_medal"),
        "seller_score": raw.get("seller_score"),
        "seller_cancellations": raw.get("seller_cancellations"),
        "seller_response_time_hours": raw.get("seller_response_time_hours"),
        "seller_completed_sales": raw.get("seller_completed_sales"),
        "photos": raw.get("photos", []),
        "url": raw.get("url"),
        "seller_id": raw.get("seller_id"),
        "seller_reputation": raw.get("seller_reputation"),
    }
