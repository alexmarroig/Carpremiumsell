from typing import Dict


COMMON_BRANDS = {
    "vw": "Volkswagen",
    "gm": "Chevrolet",
    "chevy": "Chevrolet",
}


def normalize_brand(raw_brand: str) -> str:
    key = raw_brand.strip().lower()
    return COMMON_BRANDS.get(key, raw_brand.title())


def normalize_listing_fields(raw: Dict) -> Dict:
    return {
        "external_id": raw.get("id") or raw.get("external_id"),
        "brand": normalize_brand(raw.get("brand", "")),
        "model": raw.get("model", "").title(),
        "trim": raw.get("trim"),
        "year": int(raw["year"]) if raw.get("year") else None,
        "mileage_km": raw.get("mileage_km"),
        "price": float(raw.get("price")) if raw.get("price") else None,
        "city": raw.get("city"),
        "state": raw.get("state"),
        "seller_type": raw.get("seller_type", "private"),
        "photos": raw.get("photos", []),
        "url": raw.get("url"),
    }
