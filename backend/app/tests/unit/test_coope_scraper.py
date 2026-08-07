"""Tests for the pure La Coope payload transformation used by the pilot."""

from app.modules.ingestion.infrastructure.scrapers import normalize_coope_product


def test_normalize_coope_product_keeps_the_extractable_fields() -> None:
    item = {
        "cod_interno": "12345",
        "descripcion": "Aperitivo Gancia Limon",
        "marca_desc": "Gancia",
        "precio": "5900.50",
        "gramaje": "950",
        "unimed_desc": "ML",
        "imagen": "https://lacoope.test/gancia.jpg",
    }

    product = normalize_coope_product(item, city="Comodoro Rivadavia")

    assert product == {
        "ean": "12345",
        "name": "Aperitivo Gancia Limon",
        "brand": "Gancia",
        "price": 5900.5,
        "external_id": "12345",
        "source": "lacoopeencasa",
        "identifier_type": "internal",
        "url": "https://www.lacoopeencasa.coop/articulo/12345",
        "image_url": "https://lacoope.test/gancia.jpg",
        "presentation": "950 ML",
        "city": "Comodoro Rivadavia",
    }


def test_normalize_coope_product_rejects_missing_or_non_positive_price() -> None:
    item = {
        "cod_interno": "12345",
        "descripcion": "Producto sin precio",
        "precio": 0,
    }

    assert normalize_coope_product(item) is None
