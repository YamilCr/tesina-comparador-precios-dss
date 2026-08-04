"""Pruebas del caso de uso de ranking DSS multicriterio."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import TracebackType
from uuid import UUID

import pytest

from app.modules.basket.application.dto import BasketItemInputDTO
from app.modules.catalog.domain.entities import Product, ProductSource
from app.modules.decision.application.commands import GenerateRankingCommand
from app.modules.decision.application.use_cases import GenerateRankingUseCase
from app.modules.prices.domain.entities import Price
from app.modules.supermarkets.domain.entities import Branch, Supermarket


PRODUCT_1_ID = UUID("10000000-0000-0000-0000-000000000001")
PRODUCT_2_ID = UUID("10000000-0000-0000-0000-000000000002")
SUPERMARKET_1_ID = UUID("20000000-0000-0000-0000-000000000001")
SUPERMARKET_2_ID = UUID("20000000-0000-0000-0000-000000000002")
BRANCH_1_ID = UUID("30000000-0000-0000-0000-000000000001")
BRANCH_2_ID = UUID("30000000-0000-0000-0000-000000000002")
CITY_ID = UUID("40000000-0000-0000-0000-000000000001")
SOURCE_1_ID = UUID("50000000-0000-0000-0000-000000000001")
SOURCE_2_ID = UUID("50000000-0000-0000-0000-000000000002")
SOURCE_3_ID = UUID("50000000-0000-0000-0000-000000000003")
SOURCE_4_ID = UUID("50000000-0000-0000-0000-000000000004")
OBSERVED_AT = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)


class FakeProductRepository:
    """Repositorio en memoria de productos."""

    def __init__(self, products: list[Product]) -> None:
        self._products = {product.id: product for product in products}

    async def get_by_id(self, product_id: UUID) -> Product | None:
        """Obtiene un producto por id."""
        return self._products.get(product_id)


class FakeProductSourceRepository:
    """Repositorio en memoria de productos fuente."""

    def __init__(self, product_sources: list[ProductSource]) -> None:
        self._product_sources = product_sources

    async def find_by_product(self, product_id: UUID) -> list[ProductSource]:
        """Obtiene publicaciones asociadas a un producto normalizado."""
        return [
            product_source
            for product_source in self._product_sources
            if product_source.product_id == product_id
        ]


class FakeSupermarketRepository:
    """Repositorio en memoria de supermercados."""

    def __init__(self, supermarkets: list[Supermarket]) -> None:
        self._supermarkets = {supermarket.id: supermarket for supermarket in supermarkets}

    async def get_by_id(self, supermarket_id: UUID) -> Supermarket | None:
        """Obtiene un supermercado por id."""
        return self._supermarkets.get(supermarket_id)


class FakeBranchRepository:
    """Repositorio en memoria de sucursales."""

    def __init__(self, branches: list[Branch]) -> None:
        self._branches = branches

    async def list_active(self) -> list[Branch]:
        """Lista sucursales activas."""
        return [branch for branch in self._branches if branch.active]


class FakePriceRepository:
    """Repositorio en memoria de precios."""

    def __init__(self, prices: list[Price]) -> None:
        self._prices = prices

    async def find_for_basket(
        self,
        product_ids: list[UUID],
        branch_ids: list[UUID] | None = None,
    ) -> list[Price]:
        """Devuelve precios disponibles para las sucursales solicitadas."""
        branch_filter = set(branch_ids) if branch_ids is not None else None
        return [
            price
            for price in self._prices
            if price.available and (branch_filter is None or price.branch_id in branch_filter)
        ]


class FakeUnitOfWork:
    """Unit of Work en memoria para probar la capa application."""

    def __init__(self, *, omit_second_branch_second_product: bool = False) -> None:
        products = [
            Product(id=PRODUCT_1_ID, normalized_name="Coca Cola 2.25 L"),
            Product(id=PRODUCT_2_ID, normalized_name="Leche Entera 1 L"),
        ]
        product_sources = [
            ProductSource(
                id=SOURCE_1_ID,
                product_id=PRODUCT_1_ID,
                supermarket_id=SUPERMARKET_1_ID,
                original_name="Coca Cola LA",
            ),
            ProductSource(
                id=SOURCE_2_ID,
                product_id=PRODUCT_2_ID,
                supermarket_id=SUPERMARKET_1_ID,
                original_name="Leche LA",
            ),
            ProductSource(
                id=SOURCE_3_ID,
                product_id=PRODUCT_1_ID,
                supermarket_id=SUPERMARKET_2_ID,
                original_name="Coca Cola CAR",
            ),
            ProductSource(
                id=SOURCE_4_ID,
                product_id=PRODUCT_2_ID,
                supermarket_id=SUPERMARKET_2_ID,
                original_name="Leche CAR",
            ),
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
        prices = [
            Price(
                id=UUID("60000000-0000-0000-0000-000000000001"),
                product_source_id=SOURCE_1_ID,
                branch_id=BRANCH_1_ID,
                amount=Decimal("2600"),
                observed_at=OBSERVED_AT,
            ),
            Price(
                id=UUID("60000000-0000-0000-0000-000000000002"),
                product_source_id=SOURCE_2_ID,
                branch_id=BRANCH_1_ID,
                amount=Decimal("1450"),
                observed_at=OBSERVED_AT,
            ),
            Price(
                id=UUID("60000000-0000-0000-0000-000000000003"),
                product_source_id=SOURCE_3_ID,
                branch_id=BRANCH_2_ID,
                amount=Decimal("2500"),
                observed_at=OBSERVED_AT,
            ),
        ]
        if not omit_second_branch_second_product:
            prices.append(
                Price(
                    id=UUID("60000000-0000-0000-0000-000000000004"),
                    product_source_id=SOURCE_4_ID,
                    branch_id=BRANCH_2_ID,
                    amount=Decimal("1500"),
                    observed_at=OBSERVED_AT,
                )
            )

        self.products = FakeProductRepository(products)
        self.product_sources = FakeProductSourceRepository(product_sources)
        self.supermarkets = FakeSupermarketRepository(supermarkets)
        self.branches = FakeBranchRepository(branches)
        self.prices = FakePriceRepository(prices)

    async def __aenter__(self) -> "FakeUnitOfWork":
        """Abre el contexto transaccional falso."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Cierra el contexto transaccional falso."""
        return None


def _ranking_command() -> GenerateRankingCommand:
    """Crea un command base para ranking."""
    return GenerateRankingCommand(
        items=[
            BasketItemInputDTO(product_id=PRODUCT_1_ID, quantity=Decimal("1")),
            BasketItemInputDTO(product_id=PRODUCT_2_ID, quantity=Decimal("1")),
        ],
        origin_latitude=Decimal("-45.8641"),
        origin_longitude=Decimal("-67.4966"),
    )


@pytest.mark.asyncio
async def test_generate_ranking_returns_ranked_complete_branches() -> None:
    """Debe rankear sucursales completas por score descendente."""
    response = await GenerateRankingUseCase(FakeUnitOfWork()).execute(_ranking_command())

    assert len(response.ranking) == 2
    assert response.incomplete_branches == []
    assert response.observed_at == OBSERVED_AT
    assert [result.position for result in response.ranking] == [1, 2]
    assert response.ranking[0].score >= response.ranking[1].score


@pytest.mark.asyncio
async def test_generate_ranking_reports_incomplete_branches() -> None:
    """Debe excluir del ranking sucursales que no cubren toda la canasta."""
    response = await GenerateRankingUseCase(
        FakeUnitOfWork(omit_second_branch_second_product=True)
    ).execute(_ranking_command())

    assert len(response.ranking) == 1
    assert response.ranking[0].branch.id == BRANCH_1_ID
    assert len(response.incomplete_branches) == 1
    assert response.incomplete_branches[0].branch.id == BRANCH_2_ID
    assert response.incomplete_branches[0].missing_products[0].id == PRODUCT_2_ID
