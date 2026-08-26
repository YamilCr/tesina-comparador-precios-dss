"""Caso de uso para consultar precios actuales."""

from datetime import datetime, timezone
from uuid import UUID

from app.modules.prices.application.commands import CurrentPriceQuery
from app.modules.prices.application.dto import CurrentPriceSelectionDTO, PriceDTO
from app.modules.prices.domain.services import PriceQualityPolicy
from app.shared.application import UnitOfWorkPort


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
        return (await self.execute_with_quality(query)).prices

    async def execute_with_quality(
        self,
        query: CurrentPriceQuery,
    ) -> CurrentPriceSelectionDTO:
        """Obtiene precios actuales y métricas de exclusión por calidad."""
        evaluated_at = query.as_of or datetime.now(timezone.utc)
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

            selection = PriceQualityPolicy(max_age_days=query.max_age_days).evaluate(
                prices,
                as_of=evaluated_at,
            )
            assessments = selection.assessment_by_id()
            current_prices = selection.eligible[: query.limit]
            return CurrentPriceSelectionDTO(
                prices=[
                    PriceDTO.from_entity(
                        price,
                        quality_status=assessments[price.id].status,
                        quality_reason=assessments[price.id].reason,
                        age_days=assessments[price.id].age_days,
                    )
                    for price in current_prices
                ],
                evaluated_at=evaluated_at,
                max_age_days=query.max_age_days,
                eligible_count=len(selection.eligible),
                stale_excluded_count=len(selection.stale),
                suspect_excluded_count=len(selection.suspect),
            )

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
