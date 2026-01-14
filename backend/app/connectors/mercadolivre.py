import json
import logging
import re
import time
from random import uniform
from typing import Iterable, List, Mapping, Optional

from xml.etree import ElementTree as ET

from app.core.config import get_settings
from .base import BaseConnector

logger = logging.getLogger(__name__)


LISTING_ID_PATTERN = re.compile(r"MLB\d+")


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
        classes = link.attrib.get("class", "")
        if not href or "ui-search-link" not in classes:
            continue
        if not LISTING_ID_PATTERN.search(href):
            continue
        clean = href.split("?", 1)[0]
        if clean in seen:
            continue
        seen.add(clean)
        urls.append(clean)
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
    for breadcrumb in root.iter("ol"):
        classes = breadcrumb.attrib.get("class", "")
        if "ui-pdp-breadcrumb" not in classes:
            continue
        parts = [
            _get_text(item)
            for item in breadcrumb.iter("li")
            if _get_text(item)
        ]
        if parts:
            city_state = parts[-1].split(",")
            if len(city_state) == 2:
                return city_state[0].strip(), city_state[1].strip()
    return None, None


def parse_listing_detail(html: str) -> Mapping:
    root = _parse_html(html)
    data: dict = {}

    for script in root.iter("script"):
        if script.attrib.get("type") != "application/ld+json" or not script.text:
            continue
        try:
            payload = json.loads(script.text)
            data["title"] = payload.get("name") or payload.get("description")
            offer = payload.get("offers") or {}
            if isinstance(offer, dict):
                data["price"] = offer.get("price")
            images = payload.get("image") or []
            if isinstance(images, str):
                images = [images]
            data["photos"] = images
            location = payload.get("areaServed") or payload.get("itemOffered", {}).get("itemLocation")
            if isinstance(location, dict):
                data["city"] = location.get("addressLocality")
                data["state"] = location.get("addressRegion")
        except (ValueError, TypeError):
            logger.debug("Unable to parse JSON-LD for Mercado Livre listing")

    if "title" not in data:
        title_el = root.find(".//h1")
        data["title"] = _get_text(title_el)

    if "price" not in data:
        for span in root.iter("span"):
            classes = span.attrib.get("class", "")
            if "andes-money-amount__fraction" in classes:
                data["price"] = _parse_numeric(_get_text(span))
                break

    description_el = None
    for p in root.iter("p"):
        classes = p.attrib.get("class", "")
        if "ui-pdp-description__content" in classes:
            description_el = p
            break
    if description_el:
        description = _get_text(description_el)
        if description:
            data["description"] = description

    for row in root.iter("tr"):
        classes = row.attrib.get("class", "")
        if "ui-vpp-striped-specs__table-row" not in classes:
            continue
        th = row.find("th")
        td = row.find("td")
        label = _get_text(th)
        value = _get_text(td)
        if not label or not value:
            continue
        label_lower = label.lower()
        if "quilometragem" in label_lower:
            data["mileage_km"] = _parse_numeric(value)
        elif "ano" in label_lower:
            year_val = _parse_numeric(value)
            data["year"] = int(year_val) if year_val else None

    if "city" not in data or "state" not in data:
        city, state = _extract_city_state(root)
        if city:
            data["city"] = city
        if state:
            data["state"] = state

    images = data.get("photos") or []
    if not images:
        for img in root.iter("img"):
            src = img.attrib.get("src")
            if src:
                images.append(src)
    data["photos"] = images[:10]

    if "url" not in data:
        for link in root.iter("link"):
            if link.attrib.get("rel") == "canonical" and link.attrib.get("href"):
                data["url"] = link.attrib["href"]
                break

    if data.get("title"):
        parts = data["title"].split()
        if parts:
            data.setdefault("brand", parts[0].strip())
            if len(parts) > 1:
                data.setdefault("model", " ".join(parts[1:3]).strip())

    return data


class MercadoLivreConnector(BaseConnector):
    name = "mercadolivre"

    def __init__(self, region_key: str, query_text: str = "", limit: int = 30) -> None:
        self.region_key = region_key
        self.query_text = query_text
        self.limit = limit
        self.settings = get_settings()
        self.rate_limit_per_minute = max(self.settings.mercadolivre_rate_limit_per_minute, 1)
        self.headless = self.settings.mercadolivre_headless
        self.min_delay = self.settings.mercadolivre_min_delay_seconds
        self.max_delay = self.settings.mercadolivre_max_delay_seconds

    def _delay(self) -> None:
        base_delay = max(60 / self.rate_limit_per_minute, self.min_delay)
        time.sleep(uniform(base_delay, max(base_delay, self.max_delay)))

    def _build_search_url(self) -> str:
        base = "https://carros.mercadolivre.com.br"
        parts = [base]
        if self.region_key:
            parts.append(self.region_key)
        query = self.query_text.replace(" ", "-") if self.query_text else ""
        if query:
            parts.append(f"{query}_DisplayType_LF")
        return "/".join(filter(None, parts))

    def fetch_listings(self) -> Iterable[Mapping]:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            context.route("**/*", lambda route: self._block_resources(route))
            page = context.new_page()

            search_url = self._build_search_url()
            logger.info("[mercadolivre] navigating search %s", search_url)
            page.goto(search_url, wait_until="networkidle")
            search_html = page.content()
            listing_urls = parse_search_results(search_html)[: self.limit]
            logger.info(
                "[mercadolivre] found %s listing urls for region=%s query=%s",
                len(listing_urls),
                self.region_key,
                self.query_text,
            )

            results: List[Mapping] = []
            for url in listing_urls:
                self._delay()
                page.goto(url, wait_until="domcontentloaded")
                detail_html = page.content()
                parsed = parse_listing_detail(detail_html)
                parsed["url"] = parsed.get("url") or url
                parsed["external_id"] = _extract_external_id(url)
                parsed["seller_type"] = parsed.get("seller_type") or "dealer"
                results.append(parsed)

            browser.close()
            return results

    def _block_resources(self, route) -> None:
        if route.request.resource_type in {"image", "media", "font"}:
            return route.abort()
        return route.continue_()

    def parse_listing(self, payload: Mapping) -> Mapping:
        return payload

    def normalize_fields(self, parsed: Mapping) -> Mapping:
        return parsed
