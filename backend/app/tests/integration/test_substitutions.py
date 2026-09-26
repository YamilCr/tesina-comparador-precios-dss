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
async def test_rice_product_type_is_suggested_and_revalidated(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    original_id, replacement_id, source_id, price_id = [uuid4() for _ in range(4)]
    ala_brand_id, dos_hermanos_brand_id = uuid4(), uuid4()
    async with sqlite_session_factory() as session:
        session.add_all(
            [
                BrandModel(id=ala_brand_id, nombre="Molinos Ala", activo=True),
                BrandModel(id=dos_hermanos_brand_id, nombre="Dos Hermanos", activo=True),
            ]
        )
        await session.flush()
        session.add_all(
            [
                ProductModel(
                    id=original_id,
                    nombre_normalizado="ARROZ ALA LARGO 1 KG",
                    unidad_medida="KG",
                    contenido_neto=Decimal("1"),
                    activo=True,
                ),
                ProductModel(
                    id=replacement_id,
                    marca_id=dos_hermanos_brand_id,
                    nombre_normalizado="Arroz Dos Hermanos Largo Fino 00000 1000grs",
                    unidad_medida="KG",
                    contenido_neto=Decimal("1"),
                    activo=True,
                ),
            ]
        )
        await session.flush()
        session.add(
            ProductSourceModel(
                id=source_id,
                producto_id=replacement_id,
                supermercado_id=seed_data.la_anonima_id,
                nombre_original="Arroz largo fino 00000",
                activo=True,
                confianza_match=Decimal("1"),
            )
        )
        await session.flush()
        session.add(
            PriceModel(
                id=price_id,
                producto_fuente_id=source_id,
                sucursal_id=seed_data.la_branch_id,
                precio=Decimal("1690"),
                moneda="ARS",
                disponible=True,
                promocion=False,
                fecha_relevamiento=seed_data.observed_at,
            )
        )
        await session.commit()

    items = [{"product_id": str(original_id), "quantity": "2"}]
    offered = await asgi_request(
        "POST",
        "/api/v1/decisions/substitutions",
        json_body={
            "branch_id": str(seed_data.la_branch_id),
            "items": items,
            "as_of": seed_data.observed_at.isoformat(),
        },
    )
    assert offered.status_code == 200, offered.json()
    assert offered.json()["items"][0]["candidates"][0]["product"]["id"] == str(replacement_id)

    request = {
        "city_id": str(seed_data.city_id),
        "branch_ids": [str(seed_data.la_branch_id)],
        "as_of": seed_data.observed_at.isoformat(),
        "items": items,
        "substitutions": [
            {
                "branch_id": str(seed_data.la_branch_id),
                "original_product_id": str(original_id),
                "replacement_product_id": str(replacement_id),
            }
        ],
    }
    accepted = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert accepted.status_code == 200, accepted.json()
    assert Decimal(accepted.json()["ranking"][0]["total_cost"]) == 3380

    async with sqlite_session_factory() as session:
        replacement = await session.get(ProductModel, replacement_id)
        replacement.nombre_normalizado = "Fideos Dos Hermanos Integral 1000grs"
        await session.commit()
    rejected = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert rejected.status_code == 422
    assert rejected.json()["detail"]["code"] == "invalid_substitution"


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
        replacement.nombre_normalizado = "Yogures descremados SanCor 1000 ml"
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
    assert response.json()["items"][0]["unpriced_candidates"] == []
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
    unpriced = response.json()["items"][0]["unpriced_candidates"]
    assert len(unpriced) == 1
    assert unpriced[0]["product"]["id"] == str(scenario["replacement"])
    assert unpriced[0]["price_status"] == "suspect"
    assert "unit_price" not in unpriced[0]
    assert response.json()["items"][0]["diagnostics"]["code"] == "no_suitable_prices"
    assert response.json()["items"][0]["diagnostics"]["suspect_products"] == 1
    ranking = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body=ranking_request(seed_data, scenario, substitutions=[selection(seed_data, scenario)]),
    )
    assert ranking.status_code == 200
    assert ranking.json()["incomplete_branches"][0]["substitutions"][0]["price_status"] == "suspect"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["missing", "stale"])
async def test_similar_product_without_current_price_can_be_selected(
    asgi_request, sqlite_session_factory, seed_data, scenario, status
):
    async with sqlite_session_factory() as session:
        price = await session.get(PriceModel, scenario["price"])
        if status == "missing":
            price.disponible = False
        else:
            price.fecha_relevamiento = seed_data.observed_at - timedelta(days=20)
        await session.commit()

    response = await suggestions(asgi_request, seed_data, scenario)
    assert response.status_code == 200
    group = response.json()["items"][0]
    if status == "missing":
        assert group["candidates"] == []
        assert group["diagnostics"]["code"] == "no_suitable_prices"
        candidate = group["unpriced_candidates"][0]
        assert candidate["price_status"] == "missing"
        assert "unit_price" not in candidate
    else:
        assert group["unpriced_candidates"] == []
        candidate = group["candidates"][0]
        assert candidate["price_status"] == "stale"
        assert Decimal(candidate["unit_price"]) == 1300
    assert candidate["product"]["id"] == str(scenario["replacement"])

    ranking = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body=ranking_request(
            seed_data, scenario, substitutions=[selection(seed_data, scenario)]
        ),
    )
    assert ranking.status_code == 200, ranking.json()
    if status == "missing":
        incomplete = ranking.json()["incomplete_branches"][0]
        assert incomplete["substitutions"][0]["price_status"] == "missing"
        assert incomplete["substitutions"][0]["product"]["id"] == str(scenario["replacement"])
        assert not any(item["basket_type"] == "substituted" for item in ranking.json()["ranking"])
    else:
        result = next(item for item in ranking.json()["ranking"] if item["basket_type"] == "substituted")
        assert result["has_outdated_prices"] is True
        assert Decimal(result["total_cost"]) == 2600
        assert result["substitutions"][0]["price_status"] == "stale"


@pytest.mark.asyncio
async def test_different_presentation_and_variant_are_suggested_without_quantity_conversion(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    async with sqlite_session_factory() as session:
        replacement = await session.get(ProductModel, scenario["replacement"])
        replacement.nombre_normalizado = "Leche descremada SanCor 500 ml"
        replacement.contenido_neto = Decimal("500")
        await session.commit()

    offered = await suggestions(asgi_request, seed_data, scenario)
    candidate = offered.json()["items"][0]["candidates"][0]
    assert candidate["product"]["id"] == str(scenario["replacement"])
    assert candidate["product"]["base_quantity"] == "500"
    assert candidate["quantity"] == "2"
    assert Decimal(candidate["subtotal"]) == 2600

    ranked = await asgi_request(
        "POST",
        "/api/v1/decisions/ranking",
        json_body=ranking_request(seed_data, scenario, substitutions=[selection(seed_data, scenario)]),
    )
    assert ranked.status_code == 200, ranked.json()
    result = next(item for item in ranked.json()["ranking"] if item["basket_type"] == "substituted")
    assert Decimal(result["total_cost"]) == 2600


@pytest.mark.asyncio
async def test_unpriced_product_without_chain_publication_is_rejected(
    asgi_request, sqlite_session_factory, seed_data, scenario
):
    foreign = uuid4()
    async with sqlite_session_factory() as session:
        session.add(ProductModel(id=foreign, nombre_normalizado="Leche de otra cadena 1 L", activo=True))
        await session.commit()
    request = ranking_request(
        seed_data,
        scenario,
        substitutions=[selection(seed_data, scenario, replacement_product_id=str(foreign))],
    )
    response = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_substitution"


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
    assert len(initial["incomplete_branches"]) == 1
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
    assert changed["incomplete_branches"] == []
    assert (
        next(b for b in changed["ranking"] if b["branch"]["id"] == str(seed.carrefour_branch_id))[
            "basket_type"
        ]
        == "original"
    )
    restored = (await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)).json()
    assert restored == initial


@pytest.mark.asyncio
async def test_selection_follows_chain_when_nearest_branch_changes(
    asgi_request, seed_data, scenario
):
    request = ranking_request(
        seed_data,
        scenario,
        origin_latitude="-45.85",
        origin_longitude="-67.49",
        substitutions=[selection(seed_data, scenario)],
    )
    response = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert response.status_code == 200, response.json()
    by_chain = {item["branch"]["supermarket_id"]: item for item in response.json()["ranking"]}
    la = by_chain[str(seed_data.la_anonima_id)]
    assert la["branch"]["id"] == str(scenario["sibling"])
    assert la["basket_type"] == "substituted"
    assert Decimal(la["total_cost"]) == 2600


@pytest.mark.asyncio
async def test_duplicate_substitutions_across_same_chain_are_rejected(
    asgi_request, seed_data, scenario
):
    request = ranking_request(
        seed_data,
        scenario,
        substitutions=[
            selection(seed_data, scenario),
            selection(seed_data, scenario, branch_id=str(scenario["sibling"])),
        ],
    )
    response = await asgi_request("POST", "/api/v1/decisions/ranking", json_body=request)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_substitution"


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
            ).nombre_normalizado = "Jugo de naranja 1 L"
        if mutation == "inactive":
            (await session.get(ProductModel, scenario["replacement"])).activo = False
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
    assert len(response.json()["incomplete_branches"]) == 1


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
    if mutation == "stale":
        assert response.json()["items"][0]["candidates"][0]["price_status"] == "stale"
        return
    assert response.json()["items"][0]["candidates"] == []
    diagnostic = response.json()["items"][0]["diagnostics"]
    if mutation == "unavailable":
        assert diagnostic["code"] == "no_suitable_prices"
        assert diagnostic["compatible_products"] == 1
        assert response.json()["items"][0]["unpriced_candidates"][0]["price_status"] == "missing"
    else:
        assert diagnostic["code"] in {"no_chain_products", "no_compatible_products"}
