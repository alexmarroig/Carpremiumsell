from pathlib import Path

from app.connectors.mercadolivre import _extract_external_id, parse_listing_detail, parse_search_results

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_search_results_returns_urls():
    html = _read_fixture("mercadolivre_search.html")
    urls = parse_search_results(html)
    assert len(urls) == 2
    assert urls[0].endswith("MLB123456789-fi")
    assert urls[1].endswith("MLB987654321-fi")


def test_parse_listing_detail_extracts_fields():
    html = _read_fixture("mercadolivre_detail.html")
    parsed = parse_listing_detail(html)
    assert parsed["title"] == "Toyota Corolla 2020 XEI"
    assert parsed["brand"] == "Toyota"
    assert parsed["model"] == "Corolla 2020"
    assert parsed["year"] == 2020
    assert parsed["mileage_km"] == 42000
    assert parsed["price"] == 98500
    assert parsed["city"] == "São Paulo"
    assert parsed["state"] == "SP"
    assert len(parsed["photos"]) == 2
    assert _extract_external_id("https://carros.mercadolivre.com.br/MLB123456789-fi") == "MLB123456789"
