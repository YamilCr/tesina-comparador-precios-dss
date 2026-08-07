"""Pruebas de application para selección y filtrado de precios actuales."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.prices.application.commands import (
    CompareProductPricesQuery,
    CurrentPriceQuery,
)
from app.modules.prices.application.use_cases import (
    CompareProductPricesUseCase,
    ListCurrentPricesUseCase,
)
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


pytestmark = pytest.mark.asyncio


async def test_current_prices_use_case_removes_historical_duplicates(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Debe conservar solo el último precio por producto fuente y sucursal."""
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    prices = await ListCurrentPricesUseCase(uow).execute(
        CurrentPriceQuery(product_ids=[seed_data.coca_product_id])
    )

    assert {price.id for price in prices} == {
        seed_data.la_coca_current_price_id,
        seed_data.carrefour_coca_price_id,
    }
    assert seed_data.la_coca_old_price_id not in {price.id for price in prices}
    assert seed_data.unavailable_price_id not in {price.id for price in prices}


async def test_current_prices_use_case_lists_all_active_branches_without_filters(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Lists current prices for every active branch."""
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    prices = await ListCurrentPricesUseCase(uow).execute(CurrentPriceQuery())

    assert {price.id for price in prices} == {
        seed_data.la_coca_current_price_id,
        seed_data.la_milk_price_id,
        seed_data.carrefour_coca_price_id,
        seed_data.carrefour_milk_price_id,
    }


async def test_current_prices_use_case_filters_by_supermarket_city_and_branch(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Debe resolver filtros de ubicación desde application."""
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    by_supermarket = await ListCurrentPricesUseCase(uow).execute(
        CurrentPriceQuery(
            product_ids=[seed_data.coca_product_id],
            supermarket_id=seed_data.la_anonima_id,
        )
    )
    by_city = await ListCurrentPricesUseCase(uow).execute(
        CurrentPriceQuery(product_ids=[seed_data.coca_product_id], city_id=seed_data.city_id)
    )
    by_branch = await ListCurrentPricesUseCase(uow).execute(
        CurrentPriceQuery(
            product_ids=[seed_data.coca_product_id],
            branch_id=seed_data.carrefour_branch_id,
        )
    )
    mismatch = await ListCurrentPricesUseCase(uow).execute(
        CurrentPriceQuery(
            product_ids=[seed_data.coca_product_id],
            branch_id=seed_data.carrefour_branch_id,
            supermarket_id=seed_data.la_anonima_id,
        )
    )

    assert [price.id for price in by_supermarket] == [seed_data.la_coca_current_price_id]
    assert {price.id for price in by_city} == {
        seed_data.la_coca_current_price_id,
        seed_data.carrefour_coca_price_id,
    }
    assert [price.id for price in by_branch] == [seed_data.carrefour_coca_price_id]
    assert mismatch == []


async def test_compare_product_prices_use_case_accepts_location_filters(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Debe comparar productos aplicando filtros de sucursal en application."""
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)

    prices = await CompareProductPricesUseCase(uow).execute(
        CompareProductPricesQuery(
            product_ids=[seed_data.coca_product_id, seed_data.milk_product_id],
            branch_id=seed_data.la_branch_id,
        )
    )

    assert {price.id for price in prices} == {
        seed_data.la_coca_current_price_id,
        seed_data.la_milk_price_id,
    }
