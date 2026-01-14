import json
import logging
import re
from typing import Callable, Iterable, List, Mapping, Optional

from xml.etree import ElementTree as ET

from .base import BaseConnector

logger = logging.getLogger(__name__)

LISTING_ID_PATTERN = re.compile(r"ID[A-Z0-9]+", re.IGNORECASE)


def _extract_external_id(url: str) -> Optional[str]:
    if not url:
        return None
    match = LISTING_ID_PATTERN.search(url)
    return match.group(0) if match else None


def _parse_html(html: str) -> ET.Element:
    return ET.fromstring(html)


def parse_search_results(html: str) -> List[str]:
    root = _parse_html(html)
    urls: List[str] = []
    seen: set[str] = set()
    for link in root.iter("a"):
        href = link.attrib.get("href")
        if not href or "olx" not in href:
            continue
        listing_id = _extract_external_id(href)
        if not listing_id:
            continue
        clean_href = href.split("?", 1)[0]
        if clean_href in seen:
            continue
        seen.add(clean_href)
        urls.append(clean_href)
    return urls


def _get_text(node: Optional[ET.Element]) -> Optional[str]:
    if node is None:
        return None
    text_parts = [node.text or ""]
    for child in node:
        text_parts.append(_get_text(child) or "")
        if child.tail:
            text_parts.append(child.tail)
    text = "".join(text_parts).strip()
    return text or None


def _parse_numeric(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    digits = re.findall(r"[\d\.]+", text.replace(".", "").replace(",", "."))
    if not digits:
        return None
    try:
        return float(digits[0])
    except ValueError:
        return None


def _extract_city_state(root: ET.Element) -> tuple[Optional[str], Optional[str]]:
    for el in root.iter():
        attrs = el.attrib
        if attrs.get("data-testid") == "ad-location" or "location" in attrs.get("class", ""):
            text = _get_text(el)
            if text and "," in text:
                city, state = text.split(",", 1)
                return city.strip(), state.strip()
    return None, None


def _parse_attributes(root: ET.Element) -> Mapping:
    data: dict = {}
    for ul in root.iter("ul"):
        if ul.attrib.get("data-testid") != "ad-features":
            continue
        for li in ul.iter("li"):
            spans = list(li.iter("span"))
            if len(spans) < 2:
                continue
            label = _get_text(spans[0]) or ""
            value = _get_text(spans[1]) or ""
            label_lower = label.lower()
            if "ano" in label_lower:
                year_val = _parse_numeric(value)
                data["year"] = int(year_val) if year_val else None
            elif "quilometragem" in label_lower:
                data["mileage_km"] = _parse_numeric(value)
            elif "marca" in label_lower:
                data["brand"] = value
            elif "modelo" in label_lower:
                data["model"] = value
    return data


def parse_listing_detail(html: str) -> Mapping:
    root = _parse_html(html)
    data: dict = {}

    for script in root.iter("script"):
        if script.attrib.get("type") != "application/ld+json" or not script.text:
            continue
        try:
            payload = json.loads(script.text)
        except (TypeError, json.JSONDecodeError):
            continue
        payloads = payload if isinstance(payload, list) else [payload]
        for entry in payloads:
            if not isinstance(entry, dict) or entry.get("@type") not in {"Product", "Car"}:
                continue
            data.setdefault("title", entry.get("name"))
            offer = entry.get("offers") or {}
            if isinstance(offer, dict) and "price" in offer:
                data.setdefault("price", _parse_numeric(str(offer.get("price"))))
            images = entry.get("image") or []
            if isinstance(images, str):
                images = [images]
            if images:
                data.setdefault("photos", images)
            data.setdefault("url", entry.get("url"))
            data.setdefault("brand", entry.get("brand"))
            data.setdefault("model", entry.get("model"))

    if "title" not in data:
        title_el = root.find(".//h1")
        data["title"] = _get_text(title_el)

    if "price" not in data:
        price_el = None
        for el in root.iter():
            if el.tag in {"span", "div"}:
                if el.attrib.get("data-testid") == "ad-price" or "price" in el.attrib.get("class", ""):
                    price_el = el
                    break
        data["price"] = _parse_numeric(_get_text(price_el))

    photos = data.get("photos") or []
    if not photos:
        for img in root.iter("img"):
            src = img.attrib.get("src")
            if src:
                photos.append(src)
    data["photos"] = photos

    attributes = _parse_attributes(root)
    data.update({k: v for k, v in attributes.items() if v is not None})

    city, state = _extract_city_state(root)
    if city:
        data.setdefault("city", city)
    if state:
        data.setdefault("state", state)

    if "brand" not in data or "model" not in data:
        title = data.get("title") or ""
        parts = title.split()
        if parts:
            data.setdefault("brand", parts[0])
            if len(parts) > 1:
                data.setdefault("model", " ".join(parts[1:3]).strip())

    if "url" not in data:
        for link in root.iter("link"):
            if link.attrib.get("rel") == "canonical" and link.attrib.get("href"):
                data["url"] = link.attrib["href"]
                break

    if data.get("url"):
        data.setdefault("external_id", _extract_external_id(data["url"]))

    return data


class OLXConnector(BaseConnector):
    name = "olx"

    def __init__(
        self,
        fetch_search_page: Callable[[int], str],
        fetch_detail_page: Callable[[str], str],
        max_pages: int = 1,
    ) -> None:
        self.fetch_search_page = fetch_search_page
        self.fetch_detail_page = fetch_detail_page
        self.max_pages = max_pages

    def fetch_listings(self) -> Iterable[Mapping]:
        for page in range(1, self.max_pages + 1):
            html = self.fetch_search_page(page)
            if not html.strip():
                break
            listing_urls = parse_search_results(html)
            if not listing_urls:
                break
            for url in listing_urls:
                detail_html = self.fetch_detail_page(url)
                parsed = self.parse_listing(detail_html)
                parsed["url"] = parsed.get("url") or url
                parsed["external_id"] = parsed.get("external_id") or _extract_external_id(url)
                parsed.setdefault("seller_type", "private")
                yield parsed

    def parse_listing(self, payload: Mapping) -> Mapping:
        if isinstance(payload, str):
            return parse_listing_detail(payload)
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
