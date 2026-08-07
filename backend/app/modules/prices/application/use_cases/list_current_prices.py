"""Caso de uso para consultar precios actuales."""

from uuid import UUID

from app.modules.prices.application.commands import CurrentPriceQuery
from app.modules.prices.application.dto import PriceDTO
from app.shared.application import UnitOfWorkPort

from .current_price_selection import select_current_prices


class ListCurrentPricesUseCase:
    """Consulta precios actuales sin exponer modelos de persistencia.

    Este caso de uso define "precio actual" como el último precio disponible
    por producto fuente y sucursal. También resuelve filtros de ubicación
    usando puertos de dominio.
    """

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: CurrentPriceQuery) -> list[PriceDTO]:
        """Obtiene precios actuales según producto, fuente y/o ubicación."""
        async with self._uow as uow:
            branch_ids = await self._resolve_branch_ids(uow, query)

            if query.product_source_id is not None:
                prices = await uow.prices.find_current_by_product_source(
                    query.product_source_id
                )
                if branch_ids is not None:
                    branch_filter = set(branch_ids)
                    prices = [price for price in prices if price.branch_id in branch_filter]
            elif query.product_ids:
                prices = await uow.prices.find_for_basket(
                    product_ids=query.product_ids,
                    branch_ids=branch_ids,
                )
            elif branch_ids is not None:
                prices = []
                for branch_id in branch_ids:
                    prices.extend(await uow.prices.find_current_by_branch(branch_id))
            else:
                prices = []
                for branch in await uow.branches.list_active():
                    prices.extend(await uow.prices.find_current_by_branch(branch.id))

            current_prices = select_current_prices(prices)[: query.limit]
            return [PriceDTO.from_entity(price) for price in current_prices]

    @staticmethod
    async def _resolve_branch_ids(
        uow: UnitOfWorkPort,
        query: CurrentPriceQuery,
    ) -> list[UUID] | None:
        """Resuelve filtros de ciudad, supermercado y sucursal.

        Si no hay filtros de ubicación, devuelve ``None`` para no restringir
        la consulta. Si los filtros no coinciden con sucursales activas,
        devuelve lista vacía.
        """
        if query.branch_id is not None:
            branch = await uow.branches.get_by_id(query.branch_id)
            if branch is None or not branch.active:
                return []
            if query.city_id is not None and branch.city_id != query.city_id:
                return []
            if (
                query.supermarket_id is not None
                and branch.supermarket_id != query.supermarket_id
            ):
                return []
            return [branch.id]

        if query.city_id is None and query.supermarket_id is None:
            return None

        if query.city_id is not None:
            branches = await uow.branches.list_by_city(query.city_id)
            if query.supermarket_id is not None:
                branches = [
                    branch
                    for branch in branches
                    if branch.supermarket_id == query.supermarket_id
                ]
        else:
            if query.supermarket_id is None:
                return []
            branches = await uow.branches.list_by_supermarket(query.supermarket_id)

        return [branch.id for branch in branches if branch.active]
