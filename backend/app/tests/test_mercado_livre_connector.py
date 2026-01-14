from pathlib import Path
from pathlib import Path
from typing import Dict

from app.connectors.mercado_livre import MercadoLivreConnector, parse_listing, parse_search_page

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_search_page_extracts_urls_and_next():
    html = _read("mercado_livre_search_page1.html")
    urls, next_url = parse_search_page(html)
    assert urls == [
        "https://carros.mercadolivre.com.br/MLB111-carro-um",
        "https://carros.mercadolivre.com.br/MLB222-carro-dois",
    ]
    assert next_url == "https://carros.mercadolivre.com.br/search?page=2"


def test_parse_listing_extracts_vehicle_and_seller_data():
    html = _read("mercado_livre_detail_one.html")
    parsed = parse_listing({"html": html, "url": "https://carros.mercadolivre.com.br/MLB111-carro-um"})
    assert parsed["id"] == "MLB111"
    assert parsed["brand"] == "Chevrolet"
    assert parsed["model"] == "Onix LT"
    assert parsed["year"] == 2022
    assert parsed["mileage_km"] == 45000
    assert parsed["price"] == 73500
    assert parsed["city"] == "São Paulo"
    assert parsed["state"] == "SP"
    assert parsed["seller_type"] == "Concessionária"
    assert parsed["seller_feedback"]["medal"] == "gold"
    assert parsed["seller_feedback"]["sales"] == 250
    assert len(parsed["photos"]) == 2


def test_normalize_fields_maps_values_into_output_schema():
    connector = MercadoLivreConnector(query="onix", session=None)
    parsed = {
        "id": "MLB123",
        "brand": "Chevrolet",
        "model": "Onix",
        "year": 2021,
        "mileage_km": 42000,
        "price": 70000,
        "city": "São Paulo",
        "state": "SP",
        "photos": ["https://example.com/pic.jpg"],
        "seller_type": "dealer",
        "url": "https://carros.mercadolivre.com.br/MLB123-onix",
        "seller_feedback": {"medal": "gold", "cancellation_rate": "1%", "response_time": "1h", "sales": 120},
    }
    normalized = connector.normalize_fields(parsed)
    assert normalized["external_id"] == "MLB123"
    assert normalized["brand"] == "Chevrolet"
    assert normalized["seller_feedback"]["sales"] == 120
    assert normalized["price"] == 70000
    assert normalized["photos"] == ["https://example.com/pic.jpg"]


def test_fetch_listings_uses_pagination_and_detail_parsing(monkeypatch):
    responses: Dict[str, str] = {
        "https://carros.mercadolivre.com.br/search": _read("mercado_livre_search_page1.html"),
        "https://carros.mercadolivre.com.br/search?page=2": _read("mercado_livre_search_page2.html"),
        "https://carros.mercadolivre.com.br/MLB111-carro-um": _read("mercado_livre_detail_one.html"),
        "https://carros.mercadolivre.com.br/MLB222-carro-dois": _read("mercado_livre_detail_two.html"),
        "https://carros.mercadolivre.com.br/MLB333-carro-tres": _read("mercado_livre_detail_three.html"),
    }

    class StubResponse:
        def __init__(self, text: str) -> None:
            self.text = text
            self.status_code = 200

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError("error")

    class StubSession:
        def __init__(self) -> None:
            self.calls = []

        def get(self, url: str, timeout: int = 15):
            self.calls.append(url)
            return StubResponse(responses[url])

    session = StubSession()
    connector = MercadoLivreConnector(query="", session=session, base_url="https://carros.mercadolivre.com.br/search", limit=5)

    listings = list(connector.fetch_listings())

    assert {item["external_id"] for item in listings} == {"MLB111", "MLB222", "MLB333"}
    assert session.calls[0] == "https://carros.mercadolivre.com.br/search"
    assert listings[0]["seller_feedback"]["medal"] == "gold"
