"""Pruebas de integración del UnitOfWork SQLAlchemy con SQLite async."""

from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.catalog.domain.entities import Brand
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


@pytest.mark.asyncio
async def test_unit_of_work_exposes_repositories_and_reads_seeded_data(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
    seed_data: IntegrationSeedData,
) -> None:
    """Verifica que el UoW instancie repositorios reales y lea datos seed."""
    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        product = await uow.products.get_by_id(seed_data.coca_product_id)
        branches = await uow.branches.list_active()
        current_prices = await uow.prices.find_for_basket(
            [seed_data.coca_product_id, seed_data.milk_product_id]
        )

    assert product is not None
    assert product.normalized_name == "Coca Cola 2.25 L"
    assert {branch.id for branch in branches} == {
        seed_data.la_branch_id,
        seed_data.carrefour_branch_id,
    }
    assert len(current_prices) == 5


@pytest.mark.asyncio
async def test_unit_of_work_commit_persists_changes(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica que el commit explícito del UoW persista los cambios."""
    brand_id = UUID("10000000-0000-0000-0000-000000000092")

    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        await uow.brands.save(Brand(id=brand_id, name="Marca Commit"))
        await uow.commit()

    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        persisted = await uow.brands.get_by_name("Marca Commit")

    assert persisted is not None
    assert persisted.id == brand_id


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_exception(
    sqlite_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Verifica rollback automático ante excepciones dentro del contexto."""
    brand_id = UUID("10000000-0000-0000-0000-000000000093")

    with pytest.raises(RuntimeError):
        async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
            await uow.brands.save(Brand(id=brand_id, name="Marca Exception Rollback"))
            raise RuntimeError("forced rollback")

    async with SQLAlchemyUnitOfWork(sqlite_session_factory) as uow:
        rolled_back = await uow.brands.get_by_name("Marca Exception Rollback")

    assert rolled_back is None
