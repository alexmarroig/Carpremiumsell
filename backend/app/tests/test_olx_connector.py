from pathlib import Path

from app.connectors.olx import OLXConnector, _extract_external_id, parse_listing_detail, parse_search_results

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_search_results_returns_listing_urls():
    html = _read_fixture("olx_search_page1.html")
    urls = parse_search_results(html)
    assert urls == [
        "https://www.olx.com/IDOLX123",
        "https://www.olx.com/IDOLX456",
    ]


def test_parse_listing_detail_extracts_core_fields():
    html = _read_fixture("olx_detail_IDOLX123.html")
    parsed = parse_listing_detail(html)
    assert parsed["title"] == "Honda Civic 2019 EX"
    assert parsed["brand"] == "Honda"
    assert parsed["model"] == "Civic"
    assert parsed["year"] == 2019
    assert parsed["mileage_km"] == 45000
    assert parsed["price"] == 89000
    assert parsed["city"] == "São Paulo"
    assert parsed["state"] == "SP"
    assert parsed["photos"] == [
        "https://images.olx.com/civic-1.jpg",
        "https://images.olx.com/civic-2.jpg",
    ]
    assert parsed["external_id"] == "IDOLX123"
    assert _extract_external_id("https://www.olx.com/IDOLX123?search=true") == "IDOLX123"


def test_normalize_fields_maps_expected_schema():
    connector = OLXConnector(lambda _page: "", lambda _url: "")
    parsed = {
        "external_id": "IDOLX123",
        "brand": "Honda",
        "model": "Civic",
        "year": 2019,
        "mileage_km": 45000,
        "price": 89000,
        "city": "São Paulo",
        "state": "SP",
        "photos": ["https://images.olx.com/civic-1.jpg"],
        "seller_type": "private",
        "url": "https://www.olx.com/IDOLX123",
    }
    normalized = connector.normalize_fields(parsed)
    assert normalized == parsed | {"trim": None}


def test_fetch_listings_handles_pagination_and_detail_parsing():
    search_pages = {
        1: _read_fixture("olx_search_page1.html"),
        2: _read_fixture("olx_search_page2.html"),
    }
    detail_pages = {
        "https://www.olx.com/IDOLX123": _read_fixture("olx_detail_IDOLX123.html"),
        "https://www.olx.com/IDOLX456": _read_fixture("olx_detail_IDOLX456.html"),
        "https://www.olx.com/IDOLX789": _read_fixture("olx_detail_IDOLX789.html"),
    }

    def fetch_search(page: int) -> str:
        return search_pages.get(page, "")

    def fetch_detail(url: str) -> str:
        return detail_pages[url]

    connector = OLXConnector(fetch_search, fetch_detail, max_pages=3)
    results = list(connector.fetch_listings())

    assert len(results) == 3
    assert results[0]["external_id"] == "IDOLX123"
    assert results[1]["city"] == "Campinas"
    assert results[2]["model"] == "T-Cross"
    assert results[-1]["price"] == 120000
