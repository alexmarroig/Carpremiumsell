from app.connectors.example_marketplace import ExampleMarketplaceConnector
from app.connectors.mercadolivre import MercadoLivreConnector
from app.connectors.olx import OlxConnector
from app.workers import jobs


def test_connector_registry_returns_mercado_livre():
    config = jobs.get_connector_config("mercado_livre")
    connector = config.factory(region_key="sp", query_text="suv", limit=5)

    assert config.base_url == "https://carros.mercadolivre.com.br"
    assert isinstance(connector, MercadoLivreConnector)


def test_connector_registry_returns_olx():
    config = jobs.get_connector_config("olx")
    connector = config.factory()

    assert config.base_url == "https://www.olx.com.br"
    assert isinstance(connector, OlxConnector)


def test_connector_registry_falls_back_to_example():
    config = jobs.get_connector_config("unknown")
    connector = config.factory()

    assert config.base_url == "https://example.com"
    assert isinstance(connector, ExampleMarketplaceConnector)
