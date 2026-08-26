"""Tests for the pure Carrefour VTEX payload transformation."""

import pytest

from app.modules.ingestion.infrastructure.scrapers import (
    CarrefourScraper,
    VtexLocationTarget,
    VtexRegionContext,
    normalize_carrefour_product,
)
from app.modules.ingestion.infrastructure.scrapers.vtex_region import (
    build_shipping_data_payload,
    get_carrefour_location_target,
)


def test_normalize_carrefour_product_uses_an_available_seller() -> None:
    item = {
        "productId": "12345",
        "productName": "Coca Cola Original 2.25 L",
        "brand": "Coca Cola",
        "linkText": "coca-cola-original-225-l",
        "items": [
            {
                "ean": "7790895000997",
                "images": [{"imageUrl": "https://carrefour.test/coca.jpg"}],
                "sellers": [
                    {"commertialOffer": {"Price": 3200, "AvailableQuantity": 0}},
                    {"commertialOffer": {"Price": 3500.5, "AvailableQuantity": 8}},
                ],
            }
        ],
    }

    product = normalize_carrefour_product(item, city="Comodoro Rivadavia")

    assert product == {
        "ean": "7790895000997",
        "name": "Coca Cola Original 2.25 L",
        "brand": "Coca Cola",
        "price": 3500.5,
        "external_id": "12345",
        "source": "carrefour",
        "identifier_type": "gtin",
        "url": "https://www.carrefour.com.ar/coca-cola-original-225-l/p",
        "image_url": "https://carrefour.test/coca.jpg",
        "presentation": None,
        "city": "Comodoro Rivadavia",
        "location_verified": False,
    }


def test_normalize_carrefour_product_rejects_no_stock_or_price() -> None:
    item = {
        "productId": "12345",
        "productName": "Producto sin stock",
        "items": [
            {
                "sellers": [
                    {"commertialOffer": {"Price": 3200, "AvailableQuantity": 0}},
                    {"commertialOffer": {"Price": 0, "AvailableQuantity": 8}},
                ]
            }
        ],
    }

    assert normalize_carrefour_product(item) is None


def test_carrefour_location_target_and_shipping_payload_use_comodoro_postal_code() -> None:
    target = get_carrefour_location_target("Comodoro Rivadavia")

    assert target == VtexLocationTarget(
        city="Comodoro Rivadavia",
        postal_code="9000",
        state="CH",
    )
    assert build_shipping_data_payload(target)["selectedAddresses"][0]["postalCode"] == "9000"


@pytest.mark.asyncio
async def test_carrefour_uses_the_confirmed_vtex_sales_channel() -> None:
    scraper = CarrefourScraper(["coca cola"])
    requested_urls: list[str] = []

    async def fake_get_json(_session, url, *, context):
        requested_urls.append(url)
        return [
            {
                "productId": "12345",
                "productName": "Coca Cola Original 2.25 L",
                "brand": "Coca Cola",
                "items": [
                    {
                        "ean": "7790895000997",
                        "sellers": [
                            {"commertialOffer": {"Price": 3500, "AvailableQuantity": 1}}
                        ],
                    }
                ],
            }
        ]

    scraper._get_json_with_retry = fake_get_json
    context = VtexRegionContext(
        target=VtexLocationTarget("Comodoro Rivadavia", "9000", "CH"),
        sales_channel="1",
    )

    products = await scraper.search_product(None, "coca cola", context=context)

    assert "&sc=1" in requested_urls[0]
    assert products[0]["location_verified"] is True
