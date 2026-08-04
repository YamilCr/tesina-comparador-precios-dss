"""Prueba técnica manual de casos de uso de lectura.

Este script no modifica datos ni confirma transacciones. Requiere que la base
configurada en DATABASE_URL tenga migraciones aplicadas y, preferentemente, el
seed inicial cargado.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.catalog.application.commands import SearchProductsQuery  # noqa: E402
from app.modules.catalog.application.use_cases import (  # noqa: E402
    ListCategoriesUseCase,
    SearchProductsUseCase,
)
from app.modules.prices.application.commands import GetCurrentPricesByBranchQuery  # noqa: E402
from app.modules.prices.application.use_cases import GetCurrentPricesByBranchUseCase  # noqa: E402
from app.modules.supermarkets.application.use_cases import (  # noqa: E402
    ListBranchesUseCase,
    ListSupermarketsUseCase,
)
from app.shared.infrastructure.database import async_session_factory  # noqa: E402
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork  # noqa: E402


async def test_read_use_cases() -> None:
    """Ejecuta lecturas mínimas con UnitOfWork y casos de uso."""
    products = await SearchProductsUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(SearchProductsQuery(query="coca", limit=10))
    categories = await ListCategoriesUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(active_only=True)
    supermarkets = await ListSupermarketsUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(active_only=True)
    branches = await ListBranchesUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(active_only=True)

    print(f"Products found for 'coca': {len(products)}")
    print(f"Active categories: {len(categories)}")
    print(f"Active supermarkets: {len(supermarkets)}")
    print(f"Active branches: {len(branches)}")

    if branches:
        prices = await GetCurrentPricesByBranchUseCase(
            SQLAlchemyUnitOfWork(async_session_factory)
        ).execute(GetCurrentPricesByBranchQuery(branch_id=branches[0].id))
        print(f"Current prices for first branch: {len(prices)}")
    else:
        print("No active branches found; skipping price query.")


def main() -> None:
    """Punto de entrada CLI."""
    try:
        asyncio.run(test_read_use_cases())
    except SQLAlchemyError as error:
        print(f"Database connection/query failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
