"""Caso de uso para consultar precios actuales por producto fuente."""

from app.modules.prices.application.commands import GetCurrentPricesByProductSourceQuery
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort

from .current_price_selection import select_current_prices


class GetCurrentPricesByProductSourceUseCase:
    """Obtiene precios vigentes de un producto fuente."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: GetCurrentPricesByProductSourceQuery) -> list[PriceDTO]:
        """Consulta precios vigentes por producto fuente y devuelve DTOs."""
        async with self._uow as uow:
            prices = await uow.prices.find_current_by_product_source(query.product_source_id)
            current_prices = select_current_prices(prices)
            return [PriceDTO.from_entity(price) for price in current_prices]
