"""Caso de uso para comparar precios actuales por producto."""

from app.modules.prices.application.commands import (
    CompareProductPricesQuery,
    CurrentPriceQuery,
)
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort

from .list_current_prices import ListCurrentPricesUseCase


class CompareProductPricesUseCase:
    """Consulta precios actuales de productos para comparación."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: CompareProductPricesQuery) -> list[PriceDTO]:
        """Compara precios actuales aplicando filtros opcionales de ubicación."""
        return await ListCurrentPricesUseCase(self._uow).execute(
            CurrentPriceQuery(
                product_ids=query.product_ids,
                branch_id=query.branch_id,
                city_id=query.city_id,
                supermarket_id=query.supermarket_id,
                limit=query.limit,
                as_of=query.as_of,
                max_age_days=query.max_age_days,
            )
        )
