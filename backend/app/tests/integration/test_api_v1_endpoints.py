"""Pruebas de integración HTTP para los endpoints v1 sin base real."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import TracebackType
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from app.dependencies import get_unit_of_work
from app.main import app
from app.modules.catalog.domain.entities import Brand, Product, ProductCategory, ProductSource
from app.modules.prices.domain.entities import Price
from app.modules.supermarkets.domain.entities import Branch, City, Province, Supermarket


CITY_ID = UUID("00000000-0000-0000-0000-000000000001")
SUPERMARKET_1_ID = UUID("00000000-0000-0000-0000-000000000011")
SUPERMARKET_2_ID = UUID("00000000-0000-0000-0000-000000000012")
BRANCH_1_ID = UUID("00000000-0000-0000-0000-000000000021")
BRANCH_2_ID = UUID("00000000-0000-0000-0000-000000000022")
CATEGORY_ID = UUID("00000000-0000-0000-0000-000000000031")
BRAND_ID = UUID("00000000-0000-0000-0000-000000000032")
PRODUCT_1_ID = UUID("00000000-0000-0000-0000-000000000041")
PRODUCT_2_ID = UUID("00000000-0000-0000-0000-000000000042")
SOURCE_1_ID = UUID("00000000-0000-0000-0000-000000000051")
SOURCE_2_ID = UUID("00000000-0000-0000-0000-000000000052")
SOURCE_3_ID = UUID("00000000-0000-0000-0000-000000000053")
SOURCE_4_ID = UUID("00000000-0000-0000-0000-000000000054")


@dataclass(frozen=True)
class ASGIResponse:
    """Respuesta mínima devuelta por el cliente ASGI de pruebas."""

    status_code: int
    body: bytes
    headers: dict[str, str]

    def json(self) -> Any:
        """Decodifica el cuerpo JSON."""
        return json.loads(self.body.decode("utf-8"))


async def _asgi_request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> ASGIResponse:
    """Ejecuta una request HTTP mínima contra la app ASGI sin TestClient."""
    body = json.dumps(json_body or {}).encode("utf-8") if json_body is not None else b""
    query_string = urlencode(query or {}, doseq=True).encode("utf-8")
    headers = [(b"host", b"testserver")]
    if json_body is not None:
        headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string,
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    messages: list[dict[str, Any]] = []
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)

    start_message = next(message for message in messages if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    response_headers = {
        key.decode("latin-1"): value.decode("latin-1")
        for key, value in start_message.get("headers", [])
    }
    return ASGIResponse(
        status_code=start_message["status"],
        body=response_body,
        headers=response_headers,
    )


def _request(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> ASGIResponse:
    """Wrapper síncrono para pytest."""
    return asyncio.run(_asgi_request(method, path, query=query, json_body=json_body))


class FakeProductCategoryRepository:
    """Repositorio en memoria de categorías para pruebas HTTP."""

    def __init__(self, categories: list[ProductCategory]) -> None:
        self._categories = categories

    async def list_active(self) -> list[ProductCategory]:
        return [category for category in self._categories if category.active]

    async def get_by_id(self, category_id: UUID) -> ProductCategory | None:
        return next((category for category in self._categories if category.id == category_id), None)


class FakeBrandRepository:
    """Repositorio en memoria de marcas para pruebas HTTP."""

    def __init__(self, brands: list[Brand]) -> None:
        self._brands = brands

    async def list_active(self) -> list[Brand]:
        return [brand for brand in self._brands if brand.active]

    async def list_all(self) -> list[Brand]:
        return self._brands

    async def get_by_id(self, brand_id: UUID) -> Brand | None:
        return next((brand for brand in self._brands if brand.id == brand_id), None)


class FakeProductRepository:
    """Repositorio en memoria de productos para pruebas HTTP."""

    def __init__(self, products: list[Product]) -> None:
        self._products = products

    async def get_by_id(self, product_id: UUID) -> Product | None:
        return next((product for product in self._products if product.id == product_id), None)

    async def search_by_name(self, query: str, limit: int = 20) -> list[Product]:
        normalized_query = query.casefold()
        return [
            product
            for product in self._products
            if normalized_query in product.normalized_name.casefold()
        ][:limit]

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[Product]:
        products = [product for product in self._products if product.active]
        return products[offset : offset + limit]


class FakeProductSourceRepository:
    """Repositorio en memoria de productos fuente para pruebas HTTP."""

    def __init__(self, product_sources: list[ProductSource]) -> None:
        self._product_sources = product_sources

    async def find_by_product(self, product_id: UUID) -> list[ProductSource]:
        return [
            source
            for source in self._product_sources
            if source.product_id == product_id
        ]

    async def get_by_id(self, product_source_id: UUID) -> ProductSource | None:
        return next(
            (source for source in self._product_sources if source.id == product_source_id),
            None,
        )


class FakeCityRepository:
    """Repositorio en memoria de ciudades para pruebas HTTP."""

    def __init__(self, cities: list[City]) -> None:
        self._cities = cities

    async def get_by_id(self, city_id: UUID) -> City | None:
        return next((city for city in self._cities if city.id == city_id), None)

    async def list_all(self) -> list[City]:
        return self._cities


class FakeProvinceRepository:
    """In-memory province repository for HTTP tests."""

    def __init__(self, provinces: list[Province]) -> None:
        self._provinces = provinces

    async def get_by_id(self, province_id: UUID) -> Province | None:
        return next((province for province in self._provinces if province.id == province_id), None)


class FakeSupermarketRepository:
    """Repositorio en memoria de supermercados para pruebas HTTP."""

    def __init__(self, supermarkets: list[Supermarket]) -> None:
        self._supermarkets = supermarkets

    async def get_by_id(self, supermarket_id: UUID) -> Supermarket | None:
        return next(
            (supermarket for supermarket in self._supermarkets if supermarket.id == supermarket_id),
            None,
        )

    async def list_active(self) -> list[Supermarket]:
        return [supermarket for supermarket in self._supermarkets if supermarket.active]


class FakeBranchRepository:
    """Repositorio en memoria de sucursales para pruebas HTTP."""

    def __init__(self, branches: list[Branch]) -> None:
        self._branches = branches

    async def list_active(self) -> list[Branch]:
        return [branch for branch in self._branches if branch.active]

    async def get_by_id(self, branch_id: UUID) -> Branch | None:
        return next((branch for branch in self._branches if branch.id == branch_id), None)

    async def list_by_city(self, city_id: UUID) -> list[Branch]:
        return [branch for branch in self._branches if branch.city_id == city_id]

    async def list_by_supermarket(self, supermarket_id: UUID) -> list[Branch]:
        return [
            branch
            for branch in self._branches
            if branch.supermarket_id == supermarket_id
        ]


class FakePriceRepository:
    """Repositorio en memoria de precios para pruebas HTTP."""

    def __init__(self, prices: list[Price], product_sources: list[ProductSource]) -> None:
        self._prices = prices
        self._product_sources_by_id = {source.id: source for source in product_sources}

    async def find_current_by_product_source(self, product_source_id: UUID) -> list[Price]:
        return [
            price
            for price in self._prices
            if price.product_source_id == product_source_id and price.available
        ]

    async def find_current_by_branch(self, branch_id: UUID) -> list[Price]:
        return [
            price
            for price in self._prices
            if price.branch_id == branch_id and price.available
        ]

    async def find_current_by_product_ids(self, product_ids: list[UUID]) -> list[Price]:
        return await self.find_for_basket(product_ids)

    async def find_history(
        self,
        product_source_id: UUID,
        branch_id: UUID | None = None,
    ) -> list[Price]:
        return [
            price
            for price in self._prices
            if price.product_source_id == product_source_id
            and (branch_id is None or price.branch_id == branch_id)
        ]

    async def find_for_basket(
        self,
        product_ids: list[UUID],
        branch_ids: list[UUID] | None = None,
    ) -> list[Price]:
        branch_filter = set(branch_ids) if branch_ids is not None else None
        product_filter = set(product_ids)
        prices = []
        for price in self._prices:
            source = self._product_sources_by_id[price.product_source_id]
            if source.product_id not in product_filter:
                continue
            if branch_filter is not None and price.branch_id not in branch_filter:
                continue
            if price.available:
                prices.append(price)
        return prices


class FakeUnitOfWork:
    """Unit of Work en memoria usado como override de dependencia HTTP."""

    def __init__(self) -> None:
        categories = [
            ProductCategory(id=CATEGORY_ID, name="Bebidas"),
        ]
        brands = [
            Brand(id=BRAND_ID, name="Coca Cola"),
        ]
        products = [
            Product(
                id=PRODUCT_1_ID,
                category_id=CATEGORY_ID,
                brand_id=BRAND_ID,
                normalized_name="Coca Cola 2.25 L",
                unit_measure="L",
                net_content=Decimal("2.25"),
                internal_code="BEB-COCA-225",
            ),
            Product(
                id=PRODUCT_2_ID,
                category_id=CATEGORY_ID,
                normalized_name="Agua Mineral 1.5 L",
                unit_measure="L",
                net_content=Decimal("1.5"),
                internal_code="BEB-AGUA-150",
            ),
        ]
        product_sources = [
            ProductSource(
                id=SOURCE_1_ID,
                product_id=PRODUCT_1_ID,
                supermarket_id=SUPERMARKET_1_ID,
                original_name="Coca Cola Sabor Original 2.25L",
                external_code="LA-COCA-225",
            ),
            ProductSource(
                id=SOURCE_2_ID,
                product_id=PRODUCT_2_ID,
                supermarket_id=SUPERMARKET_1_ID,
                original_name="Agua Mineral 1.5L",
                external_code="LA-AGUA-150",
            ),
            ProductSource(
                id=SOURCE_3_ID,
                product_id=PRODUCT_1_ID,
                supermarket_id=SUPERMARKET_2_ID,
                original_name="Gaseosa Coca Cola 2,25 L",
                external_code="CAR-COCA-225",
            ),
            ProductSource(
                id=SOURCE_4_ID,
                product_id=PRODUCT_2_ID,
                supermarket_id=SUPERMARKET_2_ID,
                original_name="Agua sin gas 1.5L",
                external_code="CAR-AGUA-150",
            ),
        ]
        province = Province(
            id=UUID("00000000-0000-0000-0000-000000000071"),
            name="Chubut",
        )
        cities = [
            City(
                id=CITY_ID,
                province_id=province.id,
                name="Comodoro Rivadavia",
                latitude=Decimal("-45.8641"),
                longitude=Decimal("-67.4966"),
            )
        ]
        supermarkets = [
            Supermarket(id=SUPERMARKET_1_ID, name="La Anónima"),
            Supermarket(id=SUPERMARKET_2_ID, name="Carrefour"),
        ]
        branches = [
            Branch(
                id=BRANCH_1_ID,
                supermarket_id=SUPERMARKET_1_ID,
                city_id=CITY_ID,
                name="Centro",
                address="San Martín 500",
                latitude=Decimal("-45.8645"),
                longitude=Decimal("-67.4820"),
            ),
            Branch(
                id=BRANCH_2_ID,
                supermarket_id=SUPERMARKET_2_ID,
                city_id=CITY_ID,
                name="Comodoro",
                address="Av. Hipólito Yrigoyen 2600",
                latitude=Decimal("-45.8750"),
                longitude=Decimal("-67.5100"),
            ),
        ]
        observed_at = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
        prices = [
            Price(
                id=UUID("00000000-0000-0000-0000-000000000061"),
                product_source_id=SOURCE_1_ID,
                branch_id=BRANCH_1_ID,
                amount=Decimal("2600"),
                observed_at=observed_at,
            ),
            Price(
                id=UUID("00000000-0000-0000-0000-000000000062"),
                product_source_id=SOURCE_2_ID,
                branch_id=BRANCH_1_ID,
                amount=Decimal("900"),
                observed_at=observed_at,
            ),
            Price(
                id=UUID("00000000-0000-0000-0000-000000000063"),
                product_source_id=SOURCE_3_ID,
                branch_id=BRANCH_2_ID,
                amount=Decimal("2500"),
                observed_at=observed_at,
            ),
            Price(
                id=UUID("00000000-0000-0000-0000-000000000064"),
                product_source_id=SOURCE_4_ID,
                branch_id=BRANCH_2_ID,
                amount=Decimal("950"),
                observed_at=observed_at,
            ),
        ]

        self.product_categories = FakeProductCategoryRepository(categories)
        self.brands = FakeBrandRepository(brands)
        self.products = FakeProductRepository(products)
        self.product_sources = FakeProductSourceRepository(product_sources)
        self.provinces = FakeProvinceRepository([province])
        self.cities = FakeCityRepository(cities)
        self.supermarkets = FakeSupermarketRepository(supermarkets)
        self.branches = FakeBranchRepository(branches)
        self.prices = FakePriceRepository(prices, product_sources)

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def _install_fake_unit_of_work() -> None:
    """Instala el override de dependencia para endpoints que usan UoW."""
    app.dependency_overrides[get_unit_of_work] = FakeUnitOfWork


def _clear_overrides() -> None:
    """Limpia overrides para no contaminar otros tests."""
    app.dependency_overrides.clear()


def test_catalog_products_endpoint_uses_application_use_case() -> None:
    """Verifica búsqueda HTTP de productos a través de casos de uso."""
    _install_fake_unit_of_work()
    try:
        response = _request("GET", "/api/v1/catalog/products", query={"q": "coca"})
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["count"] == 1
    assert payload["items"][0]["id"] == str(PRODUCT_1_ID)
    assert payload["items"][0]["normalized_name"] == "Coca Cola 2.25 L"


def test_reference_endpoints_return_seeded_items() -> None:
    """Verifica endpoints de referencia de categorías, ciudades, supermercados y sucursales."""
    _install_fake_unit_of_work()
    try:
        categories = _request("GET", "/api/v1/catalog/categories").json()
        brands = _request("GET", "/api/v1/catalog/brands").json()
        cities = _request("GET", "/api/v1/locations/cities").json()
        supermarkets = _request("GET", "/api/v1/supermarkets").json()
        branches = _request("GET", "/api/v1/branches").json()
    finally:
        _clear_overrides()

    assert categories["items"][0]["name"] == "Bebidas"
    assert categories["count"] == 1
    assert brands["items"][0]["name"] == "Coca Cola"
    assert brands["count"] == 1
    assert cities["items"][0]["name"] == "Comodoro Rivadavia"
    assert cities["items"][0]["province_name"] == "Chubut"
    assert cities["count"] == 1
    assert {item["name"] for item in supermarkets["items"]} == {"La Anónima", "Carrefour"}
    assert supermarkets["count"] == 2
    assert branches["pagination"]["count"] == 2
    assert branches["pagination"]["total"] == 2


def test_current_prices_endpoint_returns_prices_for_product() -> None:
    """Verifica consulta HTTP de precios vigentes por producto."""
    _install_fake_unit_of_work()
    try:
        response = _request(
            "GET",
            "/api/v1/prices/current",
            query={"product_id": str(PRODUCT_1_ID)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {item["branch_id"] for item in payload["items"]} == {
        str(BRANCH_1_ID),
        str(BRANCH_2_ID),
    }


def test_price_history_endpoint_returns_history_for_product_source() -> None:
    """Verifica consulta HTTP de historial de precios."""
    _install_fake_unit_of_work()
    try:
        response = _request(
            "GET",
            "/api/v1/prices/history",
            query={"product_source_id": str(SOURCE_1_ID)},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["items"][0]["product_source_id"] == str(SOURCE_1_ID)


def test_compare_prices_endpoint_returns_prices_for_products() -> None:
    """Verifica comparación HTTP de precios por productos normalizados."""
    _install_fake_unit_of_work()
    try:
        response = _request(
            "GET",
            "/api/v1/prices/compare",
            query={"product_ids": [str(PRODUCT_1_ID), str(PRODUCT_2_ID)]},
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
    assert {item["product_id"] for item in payload["items"]} == {
        str(PRODUCT_1_ID),
        str(PRODUCT_2_ID),
    }


def test_basket_validate_endpoint_does_not_persist_data() -> None:
    """Verifica validación HTTP de canasta temporal."""
    response = _request(
        "POST",
        "/api/v1/basket/validate",
        json_body={
            "items": [
                {"product_id": str(PRODUCT_1_ID), "quantity": "2"},
                {"product_id": str(PRODUCT_2_ID), "quantity": "1"},
            ]
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_items"] == 2
    assert payload["product_ids"] == [str(PRODUCT_1_ID), str(PRODUCT_2_ID)]


def test_decision_ranking_endpoint_returns_ranked_alternatives() -> None:
    """Verifica cálculo HTTP de ranking DSS en memoria."""
    _install_fake_unit_of_work()
    try:
        response = _request(
            "POST",
            "/api/v1/decisions/ranking",
            json_body={
                "origin_latitude": "-45.8641",
                "origin_longitude": "-67.4966",
                "items": [
                    {"product_id": str(PRODUCT_1_ID), "quantity": "1"},
                    {"product_id": str(PRODUCT_2_ID), "quantity": "1"},
                ],
            },
        )
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["ranking"]) == 2
    assert payload["ranking"][0]["position"] == 1
    assert payload["ranking"][0]["branch"]["supermarket_name"] in {"La Anónima", "Carrefour"}
    assert payload["incomplete_branches"] == []


def test_current_prices_endpoint_lists_all_prices_without_filters() -> None:
    """Verifica el contrato estándar de error HTTP."""
    _install_fake_unit_of_work()
    try:
        response = _request("GET", "/api/v1/prices/current")
    finally:
        _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 4
