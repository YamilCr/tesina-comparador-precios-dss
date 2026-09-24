"""Controlled SQL/HTTP flow, without scrapers, vectors or model downloads."""

from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from app.dependencies import get_product_search_index
from app.main import app
from app.modules.catalog.infrastructure.persistence import (
    BrandModel,
    ProductModel,
    ProductSourceModel,
)
from app.modules.prices.infrastructure.persistence import PriceModel
from app.modules.supermarkets.infrastructure.persistence import BranchModel


class BrokenIndex:
    async def search(self, query, top_k):
        raise RuntimeError("Controlled vector outage")


@pytest.mark.asyncio
async def test_wording_normalization_is_revalidated_by_ranking(
    asgi_request,
    sqlite_session_factory,
    seed_data,
    scenario,
):
    async with sqlite_session_factory() as session:
        replacement = await session.get(ProductModel, scenario["replacement"])
        replacement.nombre_normalizado = "Leches enteras SanCor 1000 ml"
        await session.commit()
    offered = await suggestions(asgi_request, seed_data, scenario)
    assert offered.json()["items"][0]["candidates"][0]["product"]["id"] == str(
        scenario["replacement"]
    )
    request = ranking_request(seed_data, scenario, substitutions=[selection(seed_data, scenario)])
    accepted = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert accepted.status_code == 200
    assert any(item["basket_type"] == "substituted" for item in accepted.json()["ranking"])
    async with sqlite_session_factory() as session:
        replacement = await session.get(ProductModel, scenario["replacement"])
        replacement.nombre_normalizado = "Leches descremadas SanCor 1000 ml"
        await session.commit()
    rejected = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "invalid_substitution"


@pytest.mark.asyncio
async def test_suggestions_without_any_initial_complete_basket(asgi_request, seed_data, scenario):
    request = ranking_request(seed_data, scenario, branch_ids=[str(seed_data.la_branch_id)])
    response = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert response.json()["ranking"] == []
    assert len(response.json()["incomplete_branches"]) == 1
    offered = await suggestions(asgi_request, seed_data, scenario)
    assert len(offered.json()["items"][0]["candidates"]) == 1
    response = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body={
            **request,
            "substitutions": [selection(seed_data, scenario)],
        },
    )
    assert len(response.json()["ranking"]) == 1


@pytest.mark.asyncio
async def test_suggestions_limit_and_cost_name_order(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    async with sqlite_session_factory() as session:
        for name, amount in [
            ("Leche Entera 1 L", 1100),
            ("leche entera 1000 ml", 1000),
            ("LECHE ENTERA 1 litro", 1200),
            ("Leche entera 1000ml", 1200),
        ]:
            product_id, source_id = uuid4(), uuid4()
            session.add(ProductModel(id=product_id, nombre_normalizado=name, activo=True))
            await session.flush()
            session.add(
                ProductSourceModel(
                    id=source_id,
                    producto_id=product_id,
                    supermercado_id=seed_data.la_anonima_id,
                    nombre_original=name,
                    activo=True,
                    confianza_match=Decimal("1"),
                )
            )
            await session.flush()
            session.add(
                PriceModel(
                    id=uuid4(),
                    producto_fuente_id=source_id,
                    sucursal_id=seed_data.la_branch_id,
                    precio=Decimal(amount),
                    moneda="ARS",
                    disponible=True,
                    promocion=False,
                    fecha_relevamiento=seed_data.observed_at,
                )
            )
        await session.commit()
    response = await suggestions(asgi_request, seed_data, scenario)
    candidates = response.json()["items"][0]["candidates"]
    assert len(candidates) == 3
    assert [Decimal(c["subtotal"]) for c in candidates] == [2000, 2200, 2400]
    assert candidates[-1]["product"]["normalized_name"] == "LECHE ENTERA 1 litro"


@pytest.mark.asyncio
async def test_anomalous_replacement_is_not_suggested(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    async with sqlite_session_factory() as session:
        for days in (1, 2):
            session.add(
                PriceModel(
                    id=uuid4(),
                    producto_fuente_id=scenario["source"],
                    sucursal_id=scenario["sibling"],
                    precio=Decimal("100"),
                    moneda="ARS",
                    disponible=True,
                    promocion=False,
                    fecha_relevamiento=seed_data.observed_at - timedelta(days=days),
                )
            )
        await session.commit()
    response = await suggestions(asgi_request, seed_data, scenario)
    assert response.json()["items"][0]["candidates"] == []
    assert response.json()["items"][0]["diagnostics"]["code"] == "no_suitable_prices"
    assert response.json()["items"][0]["diagnostics"]["suspect_products"] == 1


@pytest_asyncio.fixture
async def scenario(sqlite_session_factory, seed_data, sqlite_uow_override):
    seed = seed_data
    replacement, source, price, brand, sibling = [uuid4() for _ in range(5)]
    async with sqlite_session_factory() as session:
        (await session.get(ProductSourceModel, seed.la_milk_source_id)).activo = False
        session.add(BrandModel(id=brand, nombre="SanCor", activo=True))
        session.add(
            BranchModel(
                id=sibling,
                supermercado_id=seed.la_anonima_id,
                ciudad_id=seed.city_id,
                nombre="Otra sucursal",
                direccion="Prueba 1",
                latitud=Decimal("-45.85"),
                longitud=Decimal("-67.49"),
                activo=True,
                coordenadas_verificadas=True,
            )
        )
        session.add(
            ProductModel(
                id=replacement,
                nombre_normalizado="Leche entera SanCor 1000 ml",
                marca_id=brand,
                categoria_id=seed.category_id,
                unidad_medida="ml",
                contenido_neto=Decimal("1000"),
                activo=True,
                image_url="https://example.test/milk.jpg",
            )
        )
        await session.flush()
        session.add(
            ProductSourceModel(
                id=source,
                producto_id=replacement,
                supermercado_id=seed.la_anonima_id,
                nombre_original="Leche entera SanCor 1L",
                activo=True,
                confianza_match=Decimal("1"),
            )
        )
        await session.flush()
        session.add(
            PriceModel(
                id=price,
                producto_fuente_id=source,
                sucursal_id=sibling,
                precio=Decimal("1300"),
                moneda="ARS",
                disponible=True,
                promocion=False,
                fecha_relevamiento=seed.observed_at,
            )
        )
        await session.commit()
    app.dependency_overrides[get_product_search_index] = lambda: BrokenIndex()
    return {"replacement": replacement, "source": source, "price": price, "sibling": sibling}


def ranking_request(seed, scenario, **kwargs):
    return {
        "city_id": str(seed.city_id),
        "as_of": seed.observed_at.isoformat(),
        "items": [{"product_id": str(seed.milk_product_id), "quantity": "2"}],
        **kwargs,
    }


def selection(seed, scenario, **kwargs):
    return {
        "branch_id": str(seed.la_branch_id),
        "original_product_id": str(seed.milk_product_id),
        "replacement_product_id": str(scenario["replacement"]),
        **kwargs,
    }


async def suggestions(asgi_request, seed, scenario):
    request = ranking_request(seed, scenario)
    request.pop("city_id")
    return await asgi_request(
        "POST",
        "/api/v1/decisions/substitutions",
        json_body={
            **request,
            "branch_id": str(seed.la_branch_id),
        },
    )


@pytest.mark.asyncio
async def test_full_flow_is_scoped_and_reversible(asgi_request, seed_data, scenario, caplog):
    seed = seed_data
    response = await suggestions(asgi_request, seed, scenario)
    assert response.status_code == 200, response.json()
    candidate = response.json()["items"][0]["candidates"][0]
    assert candidate["product"]["id"] == str(scenario["replacement"])
    assert Decimal(candidate["subtotal"]) == 2600
    assert candidate["inferred_from_chain"] is True
    assert candidate["price_branch_id"] == str(scenario["sibling"])
    assert "vector retrieval failed" in caplog.text
    request = ranking_request(seed, scenario)
    initial = (await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)).json()
    assert len(initial["incomplete_branches"]) == 2
    assert all(
        b["covered_products_count"] == 0 and b["total_products_count"] == 1
        for b in initial["incomplete_branches"]
    )
    assert [Decimal(b["distance_km"]) for b in initial["incomplete_branches"]] == sorted(
        Decimal(b["distance_km"]) for b in initial["incomplete_branches"]
    )
    changed = (
        await asgi_request(
            "POST",
            "/api/v1/decisions/ranking",
            json_body={
                **request,
                "substitutions": [selection(seed, scenario)],
            },
        )
    ).json()
    assert len(changed["ranking"]) == 2
    substituted = next(b for b in changed["ranking"] if b["branch"]["id"] == str(seed.la_branch_id))
    assert substituted["basket_type"] == "substituted"
    assert Decimal(substituted["total_cost"]) == 2600
    assert substituted["substitutions"][0]["original_product_id"] == str(seed.milk_product_id)
    assert changed["incomplete_branches"][0]["branch"]["id"] == str(scenario["sibling"])
    assert (
        next(b for b in changed["ranking"] if b["branch"]["id"] == str(seed.carrefour_branch_id))[
            "basket_type"
        ]
        == "original"
    )
    restored = (await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)).json()
    assert restored == initial


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "original",
        "branch",
        "same",
        "type",
        "foreign",
        "inactive",
        "unavailable",
        "stale",
        "source",
    ],
)
async def test_manipulated_or_changed_replacements_are_rejected_atomically(
    asgi_request,
    sqlite_session_factory,
    seed_data,
    scenario,
    mutation,
):
    seed = seed_data
    assert (await suggestions(asgi_request, seed, scenario)).status_code == 200
    chosen = selection(seed, scenario)
    if mutation == "original":
        chosen["original_product_id"] = str(uuid4())
    if mutation == "branch":
        chosen["branch_id"] = str(uuid4())
    if mutation == "same":
        chosen["replacement_product_id"] = str(seed.milk_product_id)
    if mutation == "foreign":
        chosen["branch_id"] = str(seed.carrefour_branch_id)
    async with sqlite_session_factory() as session:
        if mutation == "type":
            (
                await session.get(ProductModel, scenario["replacement"])
            ).nombre_normalizado = "Leche descremada 1 L"
        if mutation == "inactive":
            (await session.get(ProductModel, scenario["replacement"])).activo = False
        if mutation == "unavailable":
            (await session.get(PriceModel, scenario["price"])).disponible = False
        if mutation == "stale":
            (await session.get(PriceModel, scenario["price"])).fecha_relevamiento = (
                seed.observed_at - timedelta(days=40)
            )
        if mutation == "source":
            (await session.get(ProductSourceModel, scenario["source"])).activo = False
        await session.commit()
    response = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body=ranking_request(
            seed,
            scenario,
            substitutions=[chosen, chosen] if mutation == "duplicate" else [chosen],
        ),
    )
    assert response.status_code == 422, response.json()
    assert response.json()["detail"]["code"] == "invalid_substitution"
    assert response.json()["detail"]["original_product_id"] == chosen["original_product_id"]


@pytest.mark.asyncio
async def test_direct_price_priority_price_changes_and_combined_quantities(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    seed = seed_data
    second_original, direct_price = uuid4(), uuid4()
    async with sqlite_session_factory() as session:
        session.add(
            ProductModel(id=second_original, nombre_normalizado="Leche Entera 1 L", activo=True)
        )
        session.add(
            PriceModel(
                id=direct_price,
                producto_fuente_id=scenario["source"],
                sucursal_id=seed.la_branch_id,
                precio=Decimal("1400"),
                moneda="ARS",
                disponible=True,
                promocion=False,
                fecha_relevamiento=seed.observed_at - timedelta(days=1),
            )
        )
        await session.commit()
    response = await suggestions(asgi_request, seed, scenario)
    candidate = response.json()["items"][0]["candidates"][0]
    assert candidate["inferred_from_chain"] is False
    assert Decimal(candidate["unit_price"]) == 1400
    async with sqlite_session_factory() as session:
        (await session.get(PriceModel, direct_price)).precio = Decimal("1500")
        await session.commit()
    request = ranking_request(
        seed,
        scenario,
        items=[
            {"product_id": str(seed.milk_product_id), "quantity": "2"},
            {"product_id": str(second_original), "quantity": "3"},
        ],
        substitutions=[
            selection(seed, scenario),
            selection(seed, scenario, original_product_id=str(second_original)),
        ],
    )
    response = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert response.status_code == 200, response.json()
    result = response.json()["ranking"][0]
    assert Decimal(result["total_cost"]) == 7500
    assert len(result["substitutions"]) == 2
    assert len(response.json()["incomplete_branches"]) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation", ["inactive", "source", "unavailable", "stale", "category", "foreign"]
)
async def test_suggestions_filter_ineligible_products(
    asgi_request, sqlite_session_factory, seed_data, scenario, mutation
):
    async with sqlite_session_factory() as session:
        if mutation == "inactive":
            (await session.get(ProductModel, scenario["replacement"])).activo = False
        if mutation == "source":
            (await session.get(ProductSourceModel, scenario["source"])).activo = False
        if mutation == "unavailable":
            (await session.get(PriceModel, scenario["price"])).disponible = False
        if mutation == "stale":
            (await session.get(PriceModel, scenario["price"])).fecha_relevamiento = (
                seed_data.observed_at - timedelta(days=40)
            )
        if mutation == "category":
            (await session.get(ProductModel, scenario["replacement"])).categoria_id = uuid4()
        if mutation == "foreign":
            (
                await session.get(ProductSourceModel, scenario["source"])
            ).supermercado_id = seed_data.carrefour_id
        await session.commit()
    response = await suggestions(asgi_request, seed_data, scenario)
    assert response.status_code == 200, response.json()
    assert response.json()["items"][0]["candidates"] == []
    diagnostic = response.json()["items"][0]["diagnostics"]
    if mutation in {"stale", "unavailable"}:
        assert diagnostic["code"] == "no_suitable_prices"
        assert diagnostic["compatible_products"] == 1
        assert diagnostic["stale_products"] == (1 if mutation == "stale" else 0)
    else:
        assert diagnostic["code"] in {"no_chain_products", "no_compatible_products"}
