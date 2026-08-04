"""Pruebas de integración para repositorios SQLAlchemy con SQLite async."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.catalog.domain.entities import Brand
from app.modules.catalog.infrastructure.persistence import (
    SQLAlchemyBrandRepository,
    SQLAlchemyProductRepository,
    SQLAlchemyProductSourceRepository,
)
from app.modules.prices.infrastructure.persistence import SQLAlchemyPriceRepository
from app.modules.supermarkets.infrastructure.persistence import (
    SQLAlchemyBranchRepository,
    SQLAlchemySupermarketRepository,
)

from .conftest import IntegrationSeedData


@pytest.mark.asyncio
async def test_sqlalchemy_repositories_read_seeded_catalog_and_prices(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Verifica consultas reales de catálogo, sucursales y precios."""
    async with sqlite_session_factory() as session:
        products = SQLAlchemyProductRepository(session)
        product_sources = SQLAlchemyProductSourceRepository(session)
        supermarkets = SQLAlchemySupermarketRepository(session)
        branches = SQLAlchemyBranchRepository(session)
        prices = SQLAlchemyPriceRepository(session)

        search_results = await products.search_by_name("coca")
        assert [product.id for product in search_results] == [seed_data.coca_product_id]

        product = await products.get_by_internal_code("LAC-LECHE-001")
        assert product is not None
        assert product.normalized_name == "Leche Entera 1 L"

        source = await product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "LA-COCA-225",
        )
        assert source is not None
        assert source.product_id == seed_data.coca_product_id

        active_supermarkets = await supermarkets.list_active()
        assert {supermarket.name for supermarket in active_supermarkets} == {
            "La Anónima",
            "Carrefour",
        }

        city_branches = await branches.list_by_city(seed_data.city_id)
        assert {branch.id for branch in city_branches} == {
            seed_data.la_branch_id,
            seed_data.carrefour_branch_id,
        }

        current_coca_prices = await prices.find_current_by_product_ids(
            [seed_data.coca_product_id]
        )
        assert {price.id for price in current_coca_prices} == {
            seed_data.la_coca_current_price_id,
            seed_data.la_coca_old_price_id,
            seed_data.carrefour_coca_price_id,
        }
        assert seed_data.unavailable_price_id not in {
            price.id for price in current_coca_prices
        }

        history = await prices.find_history(
            seed_data.la_coca_source_id,
            seed_data.la_branch_id,
        )
        assert [price.id for price in history] == [
            seed_data.la_coca_current_price_id,
            seed_data.la_coca_old_price_id,
        ]


@pytest.mark.asyncio
async def test_repository_save_does_not_commit_transaction(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que un repositorio haga flush, pero no commit automático."""
    brand_id = UUID("10000000-0000-0000-0000-000000000091")

    async with sqlite_session_factory() as session:
        brands = SQLAlchemyBrandRepository(session)
        saved = await brands.save(Brand(id=brand_id, name="Marca Rollback"))

        assert saved.id == brand_id
        assert await brands.get_by_name("Marca Rollback") is not None

        await session.rollback()

    async with sqlite_session_factory() as session:
        brands = SQLAlchemyBrandRepository(session)
        assert await brands.get_by_name("Marca Rollback") is None
