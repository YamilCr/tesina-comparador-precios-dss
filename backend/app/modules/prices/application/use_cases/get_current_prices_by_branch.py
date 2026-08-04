"""Caso de uso para consultar precios actuales por sucursal."""

from app.modules.prices.application.commands import GetCurrentPricesByBranchQuery
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort

from .current_price_selection import select_current_prices


class GetCurrentPricesByBranchUseCase:
    """Obtiene precios vigentes de una sucursal."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: GetCurrentPricesByBranchQuery) -> list[PriceDTO]:
        """Consulta precios vigentes por sucursal y devuelve DTOs."""
        async with self._uow as uow:
            prices = await uow.prices.find_current_by_branch(query.branch_id)
            current_prices = select_current_prices(prices)
            return [PriceDTO.from_entity(price) for price in current_prices]
