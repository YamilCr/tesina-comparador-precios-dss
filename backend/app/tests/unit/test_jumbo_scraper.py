"""Tests for the pure Jumbo payload transformation used by the pilot."""

from app.modules.ingestion.infrastructure.scrapers import normalize_jumbo_product


def test_normalize_jumbo_product_keeps_the_extractable_fields() -> None:
    item = {
        "productId": "12345",
        "productName": "Coca Cola Original 2.25 L",
        "brand": "Coca Cola",
        "linkText": "coca-cola-original-225-l",
        "items": [
            {
                "ean": "7790895000997",
                "images": [{"imageUrl": "https://jumbo.test/coca.jpg"}],
                "sellers": [{"commertialOffer": {"Price": 3500.5}}],
            }
        ],
    }

    product = normalize_jumbo_product(item, city="Comodoro Rivadavia")

    assert product == {
        "ean": "7790895000997",
        "name": "Coca Cola Original 2.25 L",
        "brand": "Coca Cola",
        "price": 3500.5,
        "external_id": "12345",
        "source": "jumbo",
        "identifier_type": "gtin",
        "url": "https://www.jumbo.com.ar/coca-cola-original-225-l/p",
        "image_url": "https://jumbo.test/coca.jpg",
        "presentation": None,
        "city": "Comodoro Rivadavia",
    }


def test_normalize_jumbo_product_rejects_missing_or_non_positive_price() -> None:
    item = {
        "productId": "12345",
        "productName": "Producto sin precio",
        "items": [{"sellers": [{"commertialOffer": {"Price": 0}}]}],
    }

    assert normalize_jumbo_product(item) is None
