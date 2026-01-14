from pathlib import Path
from typing import Iterable

import httpx
import pytest

from app.connectors.mercado_livre import (
    MercadoLivreConnector,
    _extract_external_id,
    parse_listing_detail,
    parse_search_results,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_search_results_from_html():
    html = _read_fixture("mercado_livre_search.html")
    urls = parse_search_results(html)
    assert urls == [
        "https://carros.mercadolivre.com.br/MLB111111111-fi",
        "https://carros.mercadolivre.com.br/MLB222222222-fi",
    ]


def test_parse_search_results_from_json():
    payload = {
        "results": [
            {"permalink": "https://carros.mercadolivre.com.br/MLB999999999-fi"},
            {"url": "https://carros.mercadolivre.com.br/MLB888888888-fi?some=param"},
        ]
    }
    urls = parse_search_results(payload)
    assert urls == [
        "https://carros.mercadolivre.com.br/MLB999999999-fi",
        "https://carros.mercadolivre.com.br/MLB888888888-fi?some=param",
    ]


def test_parse_listing_detail_extracts_fields():
    html = _read_fixture("mercado_livre_detail.html")
    parsed = parse_listing_detail(html)
    assert parsed["title"] == "Honda Civic 2019 EXL 2.0"
    assert parsed["brand"] == "Honda"
    assert parsed["model"] == "Civic 2019"
    assert parsed["year"] == 2019
    assert parsed["mileage_km"] == 38500
    assert parsed["price"] == 98500
    assert parsed["city"] == "São Paulo"
    assert parsed["state"] == "SP"
    assert parsed["photos"] == [
        "https://example.com/photo1.jpg",
        "https://example.com/photo2.jpg",
    ]


def test_normalize_fields_maps_expected_schema():
    parsed = {
        "brand": "Honda",
        "model": "Civic",
        "year": "2019",
        "mileage_km": "45000",
        "price": 97500,
        "city": "São Paulo",
        "state": "SP",
        "photos": ["https://example.com/photo.jpg"],
        "seller_type": "organization",
        "url": "https://carros.mercadolivre.com.br/MLB123456789-fi",
    }
    connector = MercadoLivreConnector(query="civic")
    normalized = connector.normalize_fields(parsed)
    assert normalized == {
        "external_id": "MLB123456789",
        "brand": "Honda",
        "model": "Civic",
        "year": 2019,
        "mileage_km": 45000,
        "price": 97500,
        "city": "São Paulo",
        "state": "SP",
        "photos": ["https://example.com/photo.jpg"],
        "seller_type": "organization",
        "url": "https://carros.mercadolivre.com.br/MLB123456789-fi",
    }


def test_fetch_listings_paginates_and_parses():
    search_page_one = _read_fixture("mercado_livre_search.html")
    search_page_two = _read_fixture("mercado_livre_search_page2.html")
    detail_one = _read_fixture("mercado_livre_detail.html")
    detail_two = _read_fixture("mercado_livre_detail_b.html")
    robots = "User-agent: *\nAllow: /"

    def transport(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("robots.txt"):
            return httpx.Response(200, text=robots)
        query_value = request.url.query.decode() if isinstance(request.url.query, bytes) else request.url.query
        if "page=2" in query_value:
            return httpx.Response(200, text=search_page_two)
        if request.url.path.endswith("MLB111111111-fi"):
            return httpx.Response(200, text=detail_one)
        if request.url.path.endswith("MLB222222222-fi"):
            return httpx.Response(200, text=detail_two)
        return httpx.Response(200, text=search_page_one)

    client = httpx.Client(transport=httpx.MockTransport(transport), base_url="https://carros.mercadolivre.com.br")
    connector = MercadoLivreConnector(query="civic", limit=3, client=client, request_delay=0)

    listings: Iterable[dict] = connector.fetch_listings()
    listings = list(listings)

    assert len(listings) == 3
    assert {item["external_id"] for item in listings} == {"MLB111111111", "MLB222222222"}
    first = listings[0]
    assert first["brand"] == "Honda"
    assert first["price"] == 98500
    assert first["city"] == "São Paulo"
    assert first["state"] == "SP"
    assert first["photos"]


def test_extract_external_id_handles_variations():
    assert _extract_external_id("https://carros.mercadolivre.com.br/MLB111111111-fi") == "MLB111111111"
    assert _extract_external_id("MLB222222222") == "MLB222222222"
    assert _extract_external_id("https://example.com/no-id") is None
