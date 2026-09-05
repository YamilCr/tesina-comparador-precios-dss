"""Tests for the static Maxiconsumo Magento catalog adapter."""

import pytest

from app.modules.ingestion.infrastructure.scrapers import (
    MaxiconsumoScraper,
    parse_maxiconsumo_search_html,
)


SEARCH_HTML = """
<ol class="products list items product-items">
  <li class="item product product-item">
    <div class="product-item-info" id="product-item-info_5230">
      <a class="product photo product-item-photo" href="/leche-la-lechera-18348.html">
        <img class="product-image-photo" src="/media/leche.jpg" alt="LECHE LA LECHERA 800 GR">
      </a>
      <strong class="product name product-item-name">
        <a class="product-item-link" href="/leche-la-lechera-18348.html">
          LECHE EN POLVO LA LECHERA 800 GR
        </a>
      </strong>
      <span class="product-sku"><span>SKU</span> 18348</span>
      <span class="price-label">Precio unitario por bulto cerrado</span>
      <span data-price-amount="$ 8.999,90"
            class="price-wrapper price-including-tax"><span class="price">$ 8.999,90</span></span>
      <span class="price-label">Precio unitario</span>
      <span data-price-amount="10349.88"
            class="price-wrapper price-including-tax"><span class="price">$ 10.349,88</span></span>
    </div>
  </li>
  <li class="item product product-item">
    <div class="product-item-info" id="product-item-info_9999">
      <a class="product-item-link" href="/producto-sin-precio.html">Producto sin precio</a>
      <span class="product-sku"><span>SKU</span> 9999</span>
    </div>
  </li>
</ol>
"""


def test_parse_maxiconsumo_search_uses_closed_case_unit_price() -> None:
    products = parse_maxiconsumo_search_html(SEARCH_HTML)

    assert products == [
        {
            "ean": "18348",
            "name": "LECHE EN POLVO LA LECHERA 800 GR",
            "brand": None,
            "price": 8999.9,
            "external_id": "18348",
            "source": "maxiconsumo",
            "identifier_type": "internal",
            "url": "https://www.maxiconsumo.com/leche-la-lechera-18348.html",
            "image_url": "https://www.maxiconsumo.com/media/leche.jpg",
            "presentation": None,
            "city": "Comodoro Rivadavia",
            "location_verified": True,
            "price_basis": "unit_price_closed_case",
        }
    ]


@pytest.mark.asyncio
async def test_maxiconsumo_search_filters_irrelevant_results_and_applies_limit() -> None:
    scraper = MaxiconsumoScraper(["leche"], result_limit=1)
    body = SEARCH_HTML.replace("Producto sin precio", "Leche descremada").replace(
        '<span class="product-sku"><span>SKU</span> 9999</span>',
        '<span class="product-sku"><span>SKU</span> 9999</span>'
        '<span class="price-label">Precio unitario por bulto cerrado</span>'
        '<span data-price-amount="1200" class="price-wrapper price-including-tax"></span>',
    )

    async def fake_get_html(*_args, **_kwargs):
        return body

    scraper._get_html_with_retry = fake_get_html
    products = await scraper.search_product(None, "leche")

    assert len(products) == 1
    assert products[0]["external_id"] == "18348"


def test_maxiconsumo_rejects_unconfigured_city() -> None:
    with pytest.raises(ValueError, match="only supports Comodoro Rivadavia"):
        MaxiconsumoScraper(["leche"], city="Trelew")
