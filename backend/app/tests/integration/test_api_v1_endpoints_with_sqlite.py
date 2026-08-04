"""Pruebas HTTP de integración usando SQLite async y UnitOfWork real."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from .conftest import ASGIResponse, IntegrationSeedData


@pytest.mark.asyncio
async def test_catalog_and_reference_endpoints_use_real_sqlite_data(
    sqlite_uow_override: None,
    asgi_request: Callable[..., Any],
    seed_data: IntegrationSeedData,
) -> None:
    """Verifica endpoints de catálogo y referencias contra una base real temporal."""
    products_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/catalog/products",
        query={"q": "coca"},
    )
    categories_response: ASGIResponse = await asgi_request("GET", "/api/v1/catalog/categories")
    supermarkets_response: ASGIResponse = await asgi_request("GET", "/api/v1/supermarkets")
    branches_response: ASGIResponse = await asgi_request("GET", "/api/v1/branches")

    assert products_response.status_code == 200
    products_payload = products_response.json()
    assert products_payload["pagination"]["count"] == 1
    assert products_payload["items"][0]["id"] == str(seed_data.coca_product_id)
    assert products_payload["items"][0]["category_name"] == "Bebidas"
    assert products_payload["items"][0]["brand_name"] == "Coca Cola"

    assert categories_response.status_code == 200
    assert categories_response.json()["items"][0]["name"] == "Bebidas"

    assert supermarkets_response.status_code == 200
    assert {item["name"] for item in supermarkets_response.json()["items"]} == {
        "La Anónima",
        "Carrefour",
    }

    assert branches_response.status_code == 200
    branches_payload = branches_response.json()
    assert branches_payload["pagination"]["count"] == 2
    assert {item["id"] for item in branches_payload["items"]} == {
        str(seed_data.la_branch_id),
        str(seed_data.carrefour_branch_id),
    }


@pytest.mark.asyncio
async def test_price_endpoints_use_real_sqlite_data(
    sqlite_uow_override: None,
    asgi_request: Callable[..., Any],
    seed_data: IntegrationSeedData,
) -> None:
    """Verifica precios vigentes, historial y comparación con repositorios reales."""
    current_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/prices/current",
        query={"product_id": str(seed_data.coca_product_id)},
    )
    history_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/prices/history",
        query={
            "product_source_id": str(seed_data.la_coca_source_id),
            "branch_id": str(seed_data.la_branch_id),
        },
    )
    compare_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/prices/compare",
        query={
            "product_ids": [
                str(seed_data.coca_product_id),
                str(seed_data.milk_product_id),
            ]
        },
    )
    compare_by_supermarket_response: ASGIResponse = await asgi_request(
        "GET",
        "/api/v1/prices/compare",
        query={
            "product_ids": [
                str(seed_data.coca_product_id),
                str(seed_data.milk_product_id),
            ],
            "supermarket_id": str(seed_data.la_anonima_id),
        },
    )

    assert current_response.status_code == 200
    current_payload = current_response.json()
    assert current_payload["count"] == 2
    assert {item["amount"] for item in current_payload["items"]} == {"2600.00", "2500.00"}
    assert all(item["available"] is True for item in current_payload["items"])

    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert history_payload["count"] == 2
    assert [item["id"] for item in history_payload["items"]] == [
        str(seed_data.la_coca_current_price_id),
        str(seed_data.la_coca_old_price_id),
    ]

    assert compare_response.status_code == 200
    compare_payload = compare_response.json()
    assert compare_payload["count"] == 4
    assert {item["product_id"] for item in compare_payload["items"]} == {
        str(seed_data.coca_product_id),
        str(seed_data.milk_product_id),
    }

    assert compare_by_supermarket_response.status_code == 200
    compare_by_supermarket_payload = compare_by_supermarket_response.json()
    assert compare_by_supermarket_payload["count"] == 2
    assert {item["supermarket_id"] for item in compare_by_supermarket_payload["items"]} == {
        str(seed_data.la_anonima_id)
    }


@pytest.mark.asyncio
async def test_ranking_endpoint_uses_real_sqlite_seed(
    sqlite_uow_override: None,
    asgi_request: Callable[..., Any],
    seed_data: IntegrationSeedData,
) -> None:
    """Verifica el ranking DSS usando datos reales cargados en SQLite temporal."""
    response: ASGIResponse = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body={
            "origin_latitude": "-45.8641",
            "origin_longitude": "-67.4966",
            "items": [
                {"product_id": str(seed_data.coca_product_id), "quantity": "1"},
                {"product_id": str(seed_data.milk_product_id), "quantity": "1"},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["incomplete_count"] == 0
    assert payload["incomplete_branches"] == []
    assert [item["position"] for item in payload["ranking"]] == [1, 2]
    assert {item["total_cost"] for item in payload["ranking"]} == {"4050.00", "4000.00"}
