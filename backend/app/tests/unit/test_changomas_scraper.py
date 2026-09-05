"""Tests for the Chango Mas public VTEX catalog adapter."""

import pytest

from app.modules.ingestion.infrastructure.scrapers import (
    ChangoMasScraper,
    VtexLocationTarget,
    VtexRegionContext,
    normalize_changomas_product,
)
from app.modules.ingestion.infrastructure.scrapers.vtex_region import (
    get_changomas_location_target,
)


def _product_payload(*, stock: int = 8, price: float = 12249) -> dict:
    return {
        "productId": "1140",
        "productName": "Fernet Branca 450 Ml",
        "brand": "Branca",
        "link": "https://www.masonline.com.ar/fernet-branca-450-cc-2/p",
        "items": [
            {
                "itemId": "1139",
                "ean": "7790290001179",
                "images": [{"imageUrl": "https://mas.test/fernet.jpg"}],
                "sellers": [
                    {
                        "commertialOffer": {
                            "Price": price,
                            "AvailableQuantity": stock,
                        }
                    }
                ],
            }
        ],
    }


def test_normalize_changomas_product_keeps_available_vtex_offer() -> None:
    product = normalize_changomas_product(
        _product_payload(),
        city="Comodoro Rivadavia",
        location_verified=True,
    )

    assert product == {
        "ean": "7790290001179",
        "name": "Fernet Branca 450 Ml",
        "brand": "Branca",
        "price": 12249.0,
        "external_id": "1140",
        "source": "changomas",
        "identifier_type": "gtin",
        "url": "https://www.masonline.com.ar/fernet-branca-450-cc-2/p",
        "image_url": "https://mas.test/fernet.jpg",
        "presentation": None,
        "city": "Comodoro Rivadavia",
        "location_verified": True,
        "price_basis": "online_delivery_postal_code_9000",
    }


def test_normalize_changomas_product_rejects_no_stock() -> None:
    assert normalize_changomas_product(_product_payload(stock=0)) is None


def test_changomas_location_target_is_comodoro() -> None:
    assert get_changomas_location_target("Comodoro Rivadavia") == VtexLocationTarget(
        city="Comodoro Rivadavia",
        postal_code="9000",
        state="CH",
    )


@pytest.mark.asyncio
async def test_changomas_search_uses_sales_channel_and_marks_location() -> None:
    scraper = ChangoMasScraper(["fernet branca"])
    requested_urls: list[str] = []

    async def fake_get_json(_session, url, *, context):
        requested_urls.append(url)
        return [_product_payload()]

    scraper._get_json_with_retry = fake_get_json
    context = VtexRegionContext(
        target=VtexLocationTarget("Comodoro Rivadavia", "9000", "CH"),
        sales_channel="1",
    )

    products = await scraper.search_product(None, "fernet branca", context=context)

    assert "&sc=1" in requested_urls[0]
    assert products[0]["location_verified"] is True


def test_changomas_rejects_unconfigured_city_when_resolving_location() -> None:
    with pytest.raises(LookupError, match="no configured VTEX location"):
        get_changomas_location_target("Trelew")

    with pytest.raises(ValueError, match="only supports Comodoro Rivadavia"):
        ChangoMasScraper(["fernet"], city="Trelew")
