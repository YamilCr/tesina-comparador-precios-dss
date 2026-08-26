"""Tests for La Anonima normalization and pooled browser orchestration."""

import asyncio

import pytest

from app.modules.ingestion.infrastructure.scrapers import (
    LaAnonimaScraper,
    normalize_la_anonima_product,
)
from app.modules.ingestion.infrastructure.scrapers import la_anonima_scraper as scraper_module


def test_normalize_la_anonima_product_keeps_browser_card_fields() -> None:
    product = normalize_la_anonima_product(
        {
            "id": "0231071",
            "name": "Gaseosa Cola Pet Coca Cola x 2,5 Lt.",
            "brandName": "Coca Cola",
            "price": "6.700,00",
            "link": "/gaseosa-cola-pet-coca-cola-x-2-5-lt/art_0231071/",
            "image": "https://laanonima.test/coca.jpg",
            "unit": "unidad",
        }
    )

    assert product == {
        "ean": "0231071",
        "name": "Gaseosa Cola Pet Coca Cola x 2,5 Lt.",
        "brand": "Coca Cola",
        "price": 6700.0,
        "external_id": "0231071",
        "source": "laanonima",
        "identifier_type": "internal",
        "url": (
            "https://www.laanonima.com.ar/"
            "gaseosa-cola-pet-coca-cola-x-2-5-lt/art_0231071/"
        ),
        "image_url": "https://laanonima.test/coca.jpg",
        "presentation": "unidad",
        "city": "Comodoro Rivadavia",
        "location_verified": True,
    }


def test_normalize_la_anonima_product_rejects_invalid_price() -> None:
    assert (
        normalize_la_anonima_product(
            {"id": "0231071", "name": "Producto", "price": "sin precio"}
        )
        is None
    )


@pytest.mark.asyncio
async def test_la_anonima_scraper_uses_bounded_pool_and_deduplicates(monkeypatch) -> None:
    pool_configuration = {}

    class FakePool:
        def __init__(self, *, max_workers, context_options):
            pool_configuration.update(
                max_workers=max_workers,
                user_agent=context_options["user_agent"],
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def run(self, operation):
            return await operation(object())

    monkeypatch.setattr(scraper_module, "PlaywrightWorkerPool", FakePool)
    monkeypatch.setattr(scraper_module, "_requires_dedicated_playwright_loop", lambda: False)
    scraper = LaAnonimaScraper(["coca cola", "coca"])

    async def fake_search(_page, query):
        await asyncio.sleep(0)
        return [
            {
                "external_id": "0231071",
                "name": query,
                "price": 6700,
            }
        ]

    scraper.search_product = fake_search

    products = await scraper.scrape()

    assert pool_configuration["max_workers"] == 2
    assert "Mozilla/5.0" in pool_configuration["user_agent"]
    assert len(products) == 1
    assert products[0]["external_id"] == "0231071"


@pytest.mark.asyncio
async def test_la_anonima_scraper_delegates_windows_selector_loop_to_proactor_thread(
    monkeypatch,
) -> None:
    delegated = {}
    expected = [{"external_id": "0231071", "name": "Coca Cola", "price": 6700}]

    async def fake_to_thread(operation, scraper):
        delegated["operation"] = operation
        delegated["scraper"] = scraper
        return expected

    monkeypatch.setattr(scraper_module, "_requires_dedicated_playwright_loop", lambda: True)
    monkeypatch.setattr(asyncio, "to_thread", fake_to_thread)
    scraper = LaAnonimaScraper(["coca cola"])

    products = await scraper.scrape()

    assert products == expected
    assert delegated == {
        "operation": scraper_module._run_in_proactor_loop,
        "scraper": scraper,
    }
