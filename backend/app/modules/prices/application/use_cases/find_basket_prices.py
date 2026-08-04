"""Caso de uso para obtener precios asociados a una canasta temporal."""

from app.modules.prices.application.commands import BasketPriceQuery
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort

from .current_price_selection import select_current_prices


class FindBasketPricesUseCase:
    """Consulta precios actuales para productos y sucursales opcionales."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: BasketPriceQuery) -> list[PriceDTO]:
        """Obtiene precios actuales para calcular una canasta en memoria."""
        async with self._uow as uow:
            prices = await uow.prices.find_for_basket(
                product_ids=query.product_ids,
                branch_ids=query.branch_ids,
            )
            current_prices = select_current_prices(prices)
            return [PriceDTO.from_entity(price) for price in current_prices]
