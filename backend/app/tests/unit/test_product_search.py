"""Tests for hybrid catalog product search."""

from decimal import Decimal
from uuid import UUID

import pytest

from app.modules.catalog.application.commands import SearchProductsQuery
from app.modules.catalog.application.services import (
    build_product_search_entry,
    build_product_search_query,
)
from app.modules.catalog.application.use_cases import SearchProductsUseCase
from app.modules.catalog.domain.entities import Product
from app.modules.catalog.domain.ports import ProductSearchHit
from app.modules.catalog.infrastructure.persistence.search_matching import (
    matches_product_name_query,
)


COCA_ID = UUID("20000000-0000-0000-0000-000000000001")
ZERO_ID = UUID("20000000-0000-0000-0000-000000000002")
MILK_ID = UUID("20000000-0000-0000-0000-000000000003")
INACTIVE_ID = UUID("20000000-0000-0000-0000-000000000004")
BEVERAGE_ID = UUID("20000000-0000-0000-0000-000000000010")
DAIRY_ID = UUID("20000000-0000-0000-0000-000000000011")


@pytest.mark.asyncio
async def test_search_keeps_textual_results_without_semantic_index() -> None:
    products = [
        _product(COCA_ID, "Coca Cola 2.25 L", category_id=BEVERAGE_ID),
        _product(MILK_ID, "Leche Entera 1 L", category_id=DAIRY_ID),
    ]

    result = await SearchProductsUseCase(_FakeUnitOfWork(products)).execute(
        SearchProductsQuery(query="coca cola", limit=10)
    )

    assert [product.id for product in result] == [COCA_ID]


@pytest.mark.asyncio
async def test_search_adds_semantic_results_when_textual_has_no_exact_match() -> None:
    products = [_product(COCA_ID, "Coca Cola 2.25 L")]
    index = _FakeSearchIndex([ProductSearchHit(COCA_ID, 0.82)])

    result = await SearchProductsUseCase(
        _FakeUnitOfWork(products),
        index,
        vector_search_enabled=True,
    ).execute(SearchProductsQuery(query="cocacola", limit=10))

    assert [product.id for product in result] == [COCA_ID]
    assert index.queries == [("cocacola", 30)]


@pytest.mark.asyncio
async def test_search_deduplicates_textual_and_semantic_results() -> None:
    products = [
        _product(COCA_ID, "Coca Cola 2.25 L"),
        _product(ZERO_ID, "Coca Cola Zero 2.25 L"),
    ]
    index = _FakeSearchIndex(
        [
            ProductSearchHit(COCA_ID, 0.90),
            ProductSearchHit(ZERO_ID, 0.80),
        ]
    )

    result = await SearchProductsUseCase(
        _FakeUnitOfWork(products),
        index,
        vector_search_enabled=True,
    ).execute(SearchProductsQuery(query="coca cola", limit=10))

    assert [product.id for product in result] == [COCA_ID, ZERO_ID]


@pytest.mark.asyncio
async def test_search_filters_inactive_and_category_after_semantic_lookup() -> None:
    products = [
        _product(COCA_ID, "Coca Cola 2.25 L", category_id=BEVERAGE_ID),
        _product(MILK_ID, "Leche Entera 1 L", category_id=DAIRY_ID),
        _product(INACTIVE_ID, "Gaseosa Similar", category_id=BEVERAGE_ID, active=False),
    ]
    index = _FakeSearchIndex(
        [
            ProductSearchHit(INACTIVE_ID, 0.91),
            ProductSearchHit(MILK_ID, 0.88),
            ProductSearchHit(COCA_ID, 0.87),
        ]
    )

    result = await SearchProductsUseCase(
        _FakeUnitOfWork(products),
        index,
        vector_search_enabled=True,
    ).execute(SearchProductsQuery(query="gaseosa", limit=10), category_id=BEVERAGE_ID)

    assert [product.id for product in result] == [COCA_ID]


@pytest.mark.asyncio
async def test_search_falls_back_to_textual_when_index_fails() -> None:
    products = [_product(COCA_ID, "Coca Cola 2.25 L")]

    result = await SearchProductsUseCase(
        _FakeUnitOfWork(products),
        _FailingSearchIndex(),
        vector_search_enabled=True,
    ).execute(SearchProductsQuery(query="coca cola", limit=10))

    assert [product.id for product in result] == [COCA_ID]


def test_product_search_document_builder_includes_e5_prefixes_and_metadata() -> None:
    product = _product(
        COCA_ID,
        "Coca Cola 2.25 L",
        category_id=BEVERAGE_ID,
        unit_measure="L",
        net_content=Decimal("2.250"),
        internal_code="BEB-COCA-225",
    )

    entry = build_product_search_entry(
        product,
        brand_name="Coca Cola",
        category_name="Bebidas",
    )

    assert build_product_search_query(" cocacola ") == "query: cocacola"
    assert entry.document.startswith("passage:")
    assert "producto Coca Cola 2.25 L" in entry.document
    assert "marca Coca Cola" in entry.document
    assert "categoria Bebidas" in entry.document
    assert "presentacion 2.25 L" in entry.document
    assert "codigo BEB-COCA-225" in entry.document
    assert entry.metadata["product_id"] == str(COCA_ID)
    assert entry.metadata["active"] is True


def _product(
    product_id: UUID,
    name: str,
    *,
    category_id: UUID | None = None,
    unit_measure: str | None = "L",
    net_content: Decimal | None = Decimal("2.250"),
    internal_code: str | None = None,
    active: bool = True,
) -> Product:
    return Product(
        id=product_id,
        normalized_name=name,
        category_id=category_id,
        unit_measure=unit_measure,
        net_content=net_content,
        internal_code=internal_code,
        active=active,
    )


class _FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products = products

    async def search_by_name(self, query: str, limit: int = 20) -> list[Product]:
        return [
            product
            for product in self._products
            if product.active
            and matches_product_name_query(name=product.normalized_name, query=query)
        ][:limit]

    async def list_active_by_ids(self, product_ids: list[UUID]) -> list[Product]:
        products_by_id = {
            product.id: product
            for product in self._products
            if product.active
        }
        return [
            products_by_id[product_id]
            for product_id in dict.fromkeys(product_ids)
            if product_id in products_by_id
        ]


class _FakeUnitOfWork:
    def __init__(self, products: list[Product]) -> None:
        self.products = _FakeProductRepository(products)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class _FakeSearchIndex:
    def __init__(self, hits: list[ProductSearchHit]) -> None:
        self._hits = hits
        self.queries: list[tuple[str, int]] = []

    async def search(self, query: str, top_k: int) -> list[ProductSearchHit]:
        self.queries.append((query, top_k))
        return self._hits[:top_k]


class _FailingSearchIndex:
    async def search(self, query: str, top_k: int) -> list[ProductSearchHit]:
        raise RuntimeError("index unavailable")
