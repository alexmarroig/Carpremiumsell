import json
import logging
import re
import time
from html import unescape
from typing import Iterable, List, Mapping, MutableMapping, Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from .base import BaseConnector

logger = logging.getLogger(__name__)

BASE_URL = "https://carros.mercadolivre.com.br"
LISTING_ID_PATTERN = re.compile(r"MLB\d+")
USER_AGENT = "AxisBot/1.0 (+https://github.com/)"


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _extract_external_id(url: str) -> Optional[str]:
    match = LISTING_ID_PATTERN.search(url or "")
    return match.group(0) if match else None


def parse_search_results(payload: str | Mapping[str, object]) -> List[str]:
    if isinstance(payload, Mapping):
        results: list[str] = []
        for item in payload.get("results", []):
            if not isinstance(item, Mapping):
                continue
            permalink = item.get("permalink") or item.get("url")
            if isinstance(permalink, str) and _extract_external_id(permalink):
                results.append(permalink)
        return results

    urls: list[str] = []
    for href in re.findall(r'href="([^"]*MLB\d+[^\"]*)"', payload):
        if _extract_external_id(href):
            urls.append(href.split("?", 1)[0])
    return list(dict.fromkeys(urls))


def _parse_json_ld(html: str, data: MutableMapping[str, object]) -> None:
    script_match = re.search(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I)
    if not script_match:
        return
    try:
        payload = json.loads(unescape(script_match.group(1)))
    except (TypeError, ValueError):
        return

    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, Mapping):
        return

    data.setdefault("title", payload.get("name") or payload.get("description"))

    offers = payload.get("offers")
    if isinstance(offers, Mapping):
        data.setdefault("price", offers.get("price") or offers.get("priceSpecification", {}).get("price"))

    images = payload.get("image") or []
    if isinstance(images, str):
        images = [images]
    if isinstance(images, list):
        data.setdefault("photos", [img for img in images if isinstance(img, str)])

    data.setdefault("brand", payload.get("brand"))
    data.setdefault("model", payload.get("model"))

    year = payload.get("productionDate") or payload.get("modelDate")
    if isinstance(year, str):
        data.setdefault("year", _safe_int(year))

    mileage = payload.get("mileageFromOdometer")
    if isinstance(mileage, Mapping):
        data.setdefault("mileage_km", _safe_int(str(mileage.get("value"))))

    location = payload.get("areaServed") or payload.get("itemLocation")
    if isinstance(location, Mapping):
        data.setdefault("city", location.get("addressLocality"))
        data.setdefault("state", location.get("addressRegion"))

    seller = payload.get("seller")
    if isinstance(seller, Mapping):
        seller_type = seller.get("@type") or seller.get("type")
        if isinstance(seller_type, str):
            data.setdefault("seller_type", seller_type.lower())

    canonical = payload.get("url")
    if isinstance(canonical, str):
        data.setdefault("url", canonical)


def _extract_tag_text(html: str, tag: str, class_substring: Optional[str] = None) -> Optional[str]:
    class_part = rf'[^>]*class="[^"]*{re.escape(class_substring)}[^"]*"' if class_substring else r"[^>]*"
    match = re.search(rf"<{tag}{class_part}>(.*?)</{tag}>", html, re.S | re.I)
    if not match:
        return None
    text = re.sub(r"<[^>]+>", "", match.group(1))
    text = unescape(text).strip()
    return text or None


def parse_listing_detail(html: str) -> Mapping[str, object]:
    data: MutableMapping[str, object] = {}

    _parse_json_ld(html, data)

    title = _extract_tag_text(html, "h1")
    if title:
        data.setdefault("title", title)

    price_text = _extract_tag_text(html, "span", "andes-money-amount__fraction")
    if price_text:
        clean_price = price_text.replace(".", "").replace(",", ".")
        data.setdefault("price", _safe_int(clean_price))

    breadcrumb_match = re.search(r'<ol[^>]*ui-pdp-breadcrumb[^>]*>(.*?)</ol>', html, re.S | re.I)
    if breadcrumb_match:
        items = re.findall(r'<li[^>]*>(.*?)</li>', breadcrumb_match.group(1), re.S | re.I)
        if items:
            location_text = unescape(items[-1]).strip()
            if "," in location_text:
                city, state = [part.strip() for part in location_text.split(",", 1)]
                data.setdefault("city", city or None)
                data.setdefault("state", state or None)

    for label, value in re.findall(
        r'<tr[^>]*ui-vpp-striped-specs__table-row[^>]*>\s*<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>\s*</tr>',
        html,
        re.S | re.I,
    ):
        label_lower = unescape(label).lower()
        value_text = unescape(re.sub(r"<[^>]+>", "", value))
        if "quilometragem" in label_lower:
            data.setdefault("mileage_km", _safe_int(re.sub(r"\D", "", value_text)))
        if label_lower.startswith("ano"):
            data.setdefault("year", _safe_int(re.sub(r"\D", "", value_text)))

    image_urls = data.get("photos") or re.findall(r'<img[^>]+src="([^"]+)"', html, re.I)
    data["photos"] = [url for url in image_urls if url][:10]

    canonical_match = re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"', html, re.I)
    if canonical_match:
        data.setdefault("url", canonical_match.group(1))

    title_parts = (data.get("title") or "").split()
    if title_parts:
        data.setdefault("brand", title_parts[0])
        if len(title_parts) > 1:
            derived_model = " ".join(title_parts[1:3])
            existing_model = data.get("model")
            if not existing_model or derived_model not in str(existing_model):
                data["model"] = derived_model

    return data


class MercadoLivreConnector(BaseConnector):
    name = "mercado_livre"

    def __init__(self, query: str, region: str | None = None, limit: int = 30, use_playwright: bool = False, client: Optional[httpx.Client] = None, request_delay: float = 0.5) -> None:
        self.query = query
        self.region = region
        self.limit = limit
        self.use_playwright = use_playwright
        self.request_delay = max(request_delay, 0)
        self._client = client
        self._robot_parser: Optional[RobotFileParser] = None

    def _client_or_default(self) -> httpx.Client:
        if self._client:
            return self._client
        headers = {"User-Agent": USER_AGENT}
        self._client = httpx.Client(headers=headers, timeout=15)
        return self._client

    def _build_search_url(self, page: int = 1) -> str:
        query_slug = self.query.strip().replace(" ", "-")
        parts = [BASE_URL]
        if self.region:
            parts.append(self.region.strip("/"))
        if query_slug:
            parts.append(f"{query_slug}_DisplayType_LF")
        url = "/".join(parts)
        if page > 1:
            url = f"{url}?page={page}"
        return url

    def _load_robots(self) -> RobotFileParser:
        if self._robot_parser:
            return self._robot_parser
        parser = RobotFileParser()
        robots_url = urljoin(BASE_URL, "/robots.txt")
        try:
            response = self._client_or_default().get(robots_url)
            response.raise_for_status()
            parser.parse(response.text.splitlines())
        except Exception as exc:  # pragma: no cover - network/robots failure is non-critical
            logger.warning("Unable to load robots.txt: %s", exc)
            parser.parse(["User-agent: *", "Allow: /"])
        self._robot_parser = parser
        return parser

    def _is_allowed(self, path: str) -> bool:
        parser = self._load_robots()
        return parser.can_fetch(USER_AGENT, path)

    def _sleep(self) -> None:
        if self.request_delay:
            time.sleep(self.request_delay)

    def _fetch_html(self, url: str) -> str:
        if not self._is_allowed(urlparse(url).path):
            raise PermissionError(f"Robots disallow fetching {url}")

        if self.use_playwright:
            try:
                from playwright.sync_api import sync_playwright  # type: ignore
            except Exception as exc:  # pragma: no cover - optional dependency
                logger.warning("Playwright unavailable, falling back to HTTP: %s", exc)
            else:
                with sync_playwright() as p:  # pragma: no cover - exercised in integration
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle")
                    html = page.content()
                    browser.close()
                    return html

        response = self._client_or_default().get(url)
        response.raise_for_status()
        return response.text

    def fetch_listings(self) -> Iterable[Mapping[str, object]]:
        results: list[Mapping[str, object]] = []
        page_num = 1
        while len(results) < self.limit:
            search_url = self._build_search_url(page=page_num)
            search_html = self._fetch_html(search_url)
            listing_urls = parse_search_results(search_html)
            if not listing_urls:
                break
            for url in listing_urls:
                if len(results) >= self.limit:
                    break
                self._sleep()
                detail_html = self._fetch_html(url)
                parsed = self.parse_listing({"url": url, "html": detail_html})
                results.append(self.normalize_fields(parsed))
            page_num += 1
        return results

    def parse_listing(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        html = payload.get("html") if isinstance(payload, Mapping) else None
        url = payload.get("url") if isinstance(payload, Mapping) else None
        if isinstance(html, str):
            parsed = dict(parse_listing_detail(html))
        else:  # pragma: no cover - defensive branch
            parsed = {}
        if url:
            parsed.setdefault("url", str(url))
        parsed.setdefault("external_id", _extract_external_id(parsed.get("url", "")))
        return parsed

    def normalize_fields(self, parsed: Mapping[str, object]) -> Mapping[str, object]:
        return {
            "external_id": parsed.get("external_id") or _extract_external_id(parsed.get("url", "")),
            "brand": parsed.get("brand"),
            "model": parsed.get("model"),
            "year": _safe_int(parsed.get("year")) if parsed.get("year") is not None else None,
            "mileage_km": _safe_int(parsed.get("mileage_km")) if parsed.get("mileage_km") is not None else None,
            "price": _safe_int(parsed.get("price")) if parsed.get("price") is not None else None,
            "city": parsed.get("city"),
            "state": parsed.get("state"),
            "photos": list(parsed.get("photos", []) or []),
            "seller_type": parsed.get("seller_type") or "dealer",
            "url": parsed.get("url"),
        }
