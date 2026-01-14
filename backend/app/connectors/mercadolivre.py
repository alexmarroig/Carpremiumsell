import json
import logging
import re
import time
from random import uniform
from typing import Iterable, List, Mapping, Optional

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from app.core.config import get_settings
from .base import BaseConnector

logger = logging.getLogger(__name__)


LISTING_ID_PATTERN = re.compile(r"MLB\d+")
SELLER_ID_PATTERN = re.compile(r"sellerId\"?\s*:?\s*\"?([\w-]+)")
MEDAL_PATTERN = re.compile(r"powerSellerStatus\"?\s*:?\s*\"?(\w+)")
SCORE_PATTERN = re.compile(r"transparencyScore\"?\s*:?\s*([0-9\.]+)")
CANCELLATIONS_PATTERN = re.compile(r"cancellations\"?\s*:?\s*([0-9]+)")
COMPLETED_SALES_PATTERN = re.compile(r"completed\"?\s*:?\s*([0-9]+)")
RESPONSE_TIME_PATTERN = re.compile(r"responseTime\"?\s*:?\s*([0-9\.]+)")


def _extract_external_id(url: str) -> Optional[str]:
    if not url:
        return None
    match = LISTING_ID_PATTERN.search(url)
    return match.group(0) if match else None


def parse_search_results(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    for link in soup.select("a.ui-search-link"):  # resilient top-level anchors in listings
        href = link.get("href")
        if href and LISTING_ID_PATTERN.search(href):
            urls.append(href.split("?", 1)[0])
    return list(dict.fromkeys(urls))  # preserve order, drop duplicates


def _extract_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    node = soup.select_one(selector)
    if not node:
        return None
    text = node.get_text(strip=True)
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


def _extract_city_state(soup: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    breadcrumb = soup.select_one("ol.ui-pdp-breadcrumb")
    if breadcrumb:
        parts = [item.get_text(strip=True) for item in breadcrumb.select("li") if item.get_text(strip=True)]
        if parts:
            city_state = parts[-1].split(",")
            if len(city_state) == 2:
                return city_state[0].strip(), city_state[1].strip()
    return None, None


def _extract_seller_metadata(soup: BeautifulSoup) -> dict:
    seller: dict = {"seller_origin": "mercadolivre"}
    for script in soup.find_all("script"):
        if not script.string:
            continue
        if "seller" not in script.string and "sellerId" not in script.string:
            continue

        if not seller.get("seller_id"):
            seller_match = SELLER_ID_PATTERN.search(script.string)
            if seller_match:
                seller["seller_id"] = seller_match.group(1)

        if not seller.get("seller_medal"):
            medal_match = MEDAL_PATTERN.search(script.string)
            if medal_match:
                seller["seller_medal"] = medal_match.group(1)

        if not seller.get("seller_score"):
            score_match = SCORE_PATTERN.search(script.string)
            if score_match:
                seller["seller_score"] = float(score_match.group(1))

        if seller.get("seller_cancellations") is None:
            cancel_match = CANCELLATIONS_PATTERN.search(script.string)
            if cancel_match:
                seller["seller_cancellations"] = int(cancel_match.group(1))

        if seller.get("seller_completed_sales") is None:
            sales_match = COMPLETED_SALES_PATTERN.search(script.string)
            if sales_match:
                seller["seller_completed_sales"] = int(sales_match.group(1))

        if seller.get("seller_response_time_hours") is None:
            response_match = RESPONSE_TIME_PATTERN.search(script.string)
            if response_match:
                seller["seller_response_time_hours"] = float(response_match.group(1))

    return seller


def parse_listing_detail(html: str) -> Mapping:
    soup = BeautifulSoup(html, "html.parser")
    data: dict = {}

    json_ld = soup.find("script", type="application/ld+json")
    if json_ld and json_ld.string:
        try:
            payload = json.loads(json_ld.string)
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

    data.setdefault("title", _extract_text(soup, "h1"))
    data.setdefault("price", _parse_numeric(_extract_text(soup, "span.andes-money-amount__fraction")))
    description = _extract_text(soup, "p.ui-pdp-description__content")
    if description:
        data["description"] = description

    specs = soup.select("tr.ui-vpp-striped-specs__table-row")
    for row in specs:
        label = _extract_text(row, "th")
        value = _extract_text(row, "td")
        if not label or not value:
            continue
        label_lower = label.lower()
        if "quilometragem" in label_lower:
            data["mileage_km"] = _parse_numeric(value)
        elif "ano" in label_lower:
            year_val = _parse_numeric(value)
            data["year"] = int(year_val) if year_val else None

    if "city" not in data or "state" not in data:
        city, state = _extract_city_state(soup)
        if city:
            data["city"] = city
        if state:
            data["state"] = state

    images = data.get("photos") or []
    if not images:
        images = [img.get("src") for img in soup.select("figure img") if img.get("src")]
    data["photos"] = images[:10]

    url = soup.find("link", rel="canonical")
    if url and url.get("href"):
        data["url"] = url.get("href")

    if data.get("title"):
        parts = data["title"].split()
        if parts:
            data["brand"] = parts[0].strip()
            if len(parts) > 1:
                data["model"] = " ".join(parts[1:3]).strip()

    data.update(_extract_seller_metadata(soup))

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
