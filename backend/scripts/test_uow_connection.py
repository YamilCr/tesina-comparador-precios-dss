"""Prueba de solo lectura para verificar la conexión mediante Unit of Work."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.dependencies import get_unit_of_work  # noqa: E402


async def test_uow_connection() -> None:
    """Abre una unidad de trabajo y muestra la cantidad de productos activos."""
    try:
        async with get_unit_of_work() as unit_of_work:
            products = await unit_of_work.products.list_active()
            print(f"Active products found: {len(products)}")
    except SQLAlchemyError:
        print("Could not connect to the database. Verify DATABASE_URL and migrations.")


if __name__ == "__main__":
    asyncio.run(test_uow_connection())
