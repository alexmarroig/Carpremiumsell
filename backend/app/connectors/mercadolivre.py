import json
import logging
import re
import time
from html import unescape
from random import uniform
from typing import Iterable, List, Mapping, Optional

from app.core.config import get_settings
from .base import BaseConnector

logger = logging.getLogger(__name__)


LISTING_ID_PATTERN = re.compile(r"MLB\d+")


def _extract_external_id(url: str) -> Optional[str]:
    if not url:
        return None
    match = LISTING_ID_PATTERN.search(url)
    return match.group(0) if match else None


def parse_search_results(html: str) -> List[str]:
    urls: List[str] = []
    anchor_pattern = re.compile(
        r"<a[^>]*class=\"[^\"]*ui-search-link[^\"]*\"[^>]*href=\"([^\"]+)\"",
        re.IGNORECASE,
    )
    for match in anchor_pattern.finditer(html):
        href = match.group(1)
        if href and LISTING_ID_PATTERN.search(href):
            urls.append(href.split("?", 1)[0])
    seen: List[str] = []
    for url in urls:
        if url not in seen:
            seen.append(url)
    return seen


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


def parse_listing_detail(html: str) -> Mapping:
    data: dict = {}

    json_ld_match = re.search(
        r"<script[^>]+type=\"application/ld\+json\"[^>]*>(.*?)</script>", html, re.S | re.I
    )
    if json_ld_match:
        try:
            payload = json.loads(unescape(json_ld_match.group(1)))
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

    title_match = re.search(r"<h1[^>]*>([^<]+)", html, re.I)
    if title_match and not data.get("title"):
        data["title"] = unescape(title_match.group(1)).strip()

    price_match = re.search(
        r"<span[^>]*class=\"[^\"]*andes-money-amount__fraction[^\"]*\"[^>]*>([^<]+)",
        html,
        re.I,
    )
    if price_match and "price" not in data:
        data["price"] = _parse_numeric(unescape(price_match.group(1)))

    description_match = re.search(
        r"<p[^>]*class=\"[^\"]*ui-pdp-description__content[^\"]*\"[^>]*>([^<]+)",
        html,
        re.I,
    )
    if description_match:
        data["description"] = unescape(description_match.group(1)).strip()

    specs_pattern = re.compile(
        r"<tr[^>]*class=\"[^\"]*ui-vpp-striped-specs__table-row[^\"]*\"[^>]*>\s*"
        r"<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>",
        re.S | re.I,
    )
    for match in specs_pattern.finditer(html):
        label = unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()
        value = unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        if not label or not value:
            continue
        label_lower = label.lower()
        if "quilometragem" in label_lower:
            data["mileage_km"] = _parse_numeric(value)
        elif "ano" in label_lower:
            year_val = _parse_numeric(value)
            data["year"] = int(year_val) if year_val else None

    if "photos" not in data or not data["photos"]:
        images = re.findall(r"<img[^>]*src=\"([^\"]+)\"", html, re.I)
        data["photos"] = images[:10]

    canonical_match = re.search(
        r"<link[^>]+rel=\"canonical\"[^>]+href=\"([^\"]+)\"", html, re.I
    )
    if canonical_match:
        data["url"] = canonical_match.group(1)

    if data.get("title"):
        parts = data["title"].split()
        if parts:
            data["brand"] = parts[0].strip()
            if len(parts) > 1:
                data["model"] = " ".join(parts[1:3]).strip()

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
