"""Caso de uso para consultar historial de precios."""

from app.modules.prices.application.commands import GetPriceHistoryQuery
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort


class GetPriceHistoryUseCase:
    """Obtiene historial de precios de un producto fuente."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: GetPriceHistoryQuery) -> list[PriceDTO]:
        """Consulta histórico de precios y devuelve DTOs."""
        async with self._uow as uow:
            prices = await uow.prices.find_history(query.product_source_id, query.branch_id)
            return [PriceDTO.from_entity(price) for price in prices]
