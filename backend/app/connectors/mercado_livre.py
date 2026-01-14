import json
import re
from html import unescape
from typing import Iterable, List, Mapping, Optional, Tuple

import httpx

from .base import BaseConnector


LISTING_ID_PATTERN = re.compile(r"MLB\d+", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"[\d\.]+")
KM_PATTERN = re.compile(r"([\d\.]+)\s*km", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b(20\d{2}|19\d{2})\b")


def _parse_number(text: Optional[str]) -> Optional[int]:
    if not text:
        return None
    digits = PRICE_PATTERN.findall(text.replace("\xa0", " "))
    if not digits:
        return None
    try:
        return int(digits[0].replace(".", ""))
    except ValueError:
        return None


def _extract_city_state(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not raw:
        return None, None
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, None


def _find_all_urls(html: str) -> List[str]:
    urls: List[str] = []
    for match in re.finditer(r'<a[^>]+class="[^"]*ui-search-result__content[^"]*"[^>]+href="([^"]+)"', html, re.IGNORECASE):
        href = unescape(match.group(1))
        if LISTING_ID_PATTERN.search(href):
            urls.append(href.split("?", 1)[0])
    return list(dict.fromkeys(urls))


def parse_search_page(html: str) -> Tuple[List[str], Optional[str]]:
    urls = _find_all_urls(html)
    next_match = re.search(r'<a[^>]+rel="next"[^>]+href="([^"]+)"', html, re.IGNORECASE)
    next_url = unescape(next_match.group(1)) if next_match else None
    return urls, next_url


def _extract_photos(html: str) -> List[str]:
    photos = []
    for match in re.finditer(r'<img[^>]+(?:data-src|src)="([^"]+)"', html, re.IGNORECASE):
        photos.append(unescape(match.group(1)))
    return list(dict.fromkeys(photos))


def _extract_seller_feedback(html: str) -> Mapping:
    script_match = re.search(r'<script[^>]+id="seller-reputation"[^>]*>(.*?)</script>', html, re.IGNORECASE | re.DOTALL)
    if script_match:
        try:
            data = json.loads(script_match.group(1))
            return {
                "medal": data.get("medal"),
                "cancellation_rate": data.get("cancellation_rate"),
                "response_time": data.get("response_time"),
                "sales": data.get("sales"),
            }
        except json.JSONDecodeError:
            pass
    return {}


def parse_listing(payload: Mapping) -> Mapping:
    html = payload.get("html") or ""
    url = payload.get("url")

    parsed: dict = {}
    id_match = re.search(r'data-product-id="(MLB\d+)"', html, re.IGNORECASE)
    if id_match:
        parsed["id"] = id_match.group(1)

    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        parsed["title"] = unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip()

    price_match = re.search(r'class="andes-money-amount__fraction"[^>]*>(.*?)</', html, re.IGNORECASE | re.DOTALL)
    parsed["price"] = _parse_number(price_match.group(1) if price_match else None)

    specs_text = " ".join(match.group(1) for match in re.finditer(r"<li[^>]*>(.*?)</li>", html, re.IGNORECASE | re.DOTALL))
    km_match = KM_PATTERN.search(specs_text)
    if km_match:
        parsed["mileage_km"] = _parse_number(km_match.group(1))
    year_match = YEAR_PATTERN.search(specs_text)
    if year_match:
        parsed["year"] = int(year_match.group(1))

    location_match = re.search(r'class="ui-vip-location"[^>]*>(.*?)</', html, re.IGNORECASE | re.DOTALL)
    if location_match:
        city, state = _extract_city_state(unescape(location_match.group(1)).strip())
        if city:
            parsed["city"] = city
        if state:
            parsed["state"] = state

    seller_match = re.search(r'data-testid="seller-type"[^>]*>(.*?)</', html, re.IGNORECASE | re.DOTALL)
    if seller_match:
        parsed["seller_type"] = unescape(seller_match.group(1)).strip()

    parsed["photos"] = _extract_photos(html)
    parsed["seller_feedback"] = _extract_seller_feedback(html)

    canonical_match = re.search(r'rel="canonical"[^>]+href="([^"]+)"', html, re.IGNORECASE)
    if canonical_match:
        parsed["url"] = unescape(canonical_match.group(1))
    elif url:
        parsed["url"] = url

    if parsed.get("title"):
        parts = parsed["title"].split()
        if parts:
            parsed["brand"] = parts[0]
            remaining = " ".join(parts[1:])
            remaining = YEAR_PATTERN.sub("", remaining).strip()
            if remaining:
                parsed["model"] = remaining

    if not parsed.get("id") and parsed.get("url"):
        match = LISTING_ID_PATTERN.search(parsed["url"])
        if match:
            parsed["id"] = match.group(0)

    return parsed


class MercadoLivreConnector(BaseConnector):
    name = "mercado_livre"

    def __init__(self, query: str, session: Optional[httpx.Client] = None, base_url: Optional[str] = None, limit: int = 30) -> None:
        self.query = query
        self.limit = limit
        self.session = session or httpx.Client()
        self.base_url = base_url or self._build_search_url()

    def _build_search_url(self) -> str:
        query_part = self.query.replace(" ", "-") if self.query else ""
        return f"https://carros.mercadolivre.com.br/{query_part}".rstrip("/") + "/search"

    def fetch_listings(self) -> Iterable[Mapping]:
        url = self.base_url
        fetched = 0
        while url and fetched < self.limit:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            urls, next_url = parse_search_page(response.text)
            for listing_url in urls:
                if fetched >= self.limit:
                    break
                detail_response = self.session.get(listing_url, timeout=15)
                detail_response.raise_for_status()
                parsed = parse_listing({"html": detail_response.text, "url": listing_url})
                yield self.normalize_fields(parsed)
                fetched += 1
            url = next_url

    def parse_listing(self, payload: Mapping) -> Mapping:
        return parse_listing(payload)

    def normalize_fields(self, parsed: Mapping) -> Mapping:
        return {
            "external_id": parsed.get("id"),
            "brand": parsed.get("brand"),
            "model": parsed.get("model"),
            "year": parsed.get("year"),
            "mileage_km": parsed.get("mileage_km"),
            "price": parsed.get("price"),
            "city": parsed.get("city"),
            "state": parsed.get("state"),
            "photos": parsed.get("photos", []),
            "seller_type": parsed.get("seller_type"),
            "url": parsed.get("url"),
            "seller_feedback": parsed.get("seller_feedback", {}),
        }
