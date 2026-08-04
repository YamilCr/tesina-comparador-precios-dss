"""Caso de uso para generar ranking DSS multicriterio en memoria."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.basket.application.use_cases.build_basket import BuildBasketUseCase
from app.modules.catalog.domain.entities import ProductSource
from app.modules.decision.application.commands import GenerateRankingCommand
from app.modules.decision.application.dto.ranking_dto import (
    IncompleteBranchDTO,
    MissingProductDTO,
    RankingBranchDTO,
    RankingResponseDTO,
    RankingResultDTO,
)
from app.modules.decision.domain.entities import Alternative
from app.modules.decision.domain.services import WeightedSumModel
from app.modules.geo.domain.services import HaversineDistanceService
from app.modules.geo.domain.value_objects import GeoPoint
from app.modules.prices.domain.entities import Price
from app.modules.supermarkets.domain.entities import Branch
from app.shared.application import UnitOfWorkPort


class GenerateRankingUseCase:
    """Orquesta catálogo, precios, sucursales, distancia y modelo DSS."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        basket_builder: BuildBasketUseCase | None = None,
        distance_service: HaversineDistanceService | None = None,
        ranking_model: WeightedSumModel | None = None,
    ) -> None:
        """Recibe dependencias de aplicación y servicios de dominio puros."""
        self._unit_of_work = unit_of_work
        self._basket_builder = basket_builder or BuildBasketUseCase()
        self._distance_service = distance_service or HaversineDistanceService()
        self._ranking_model = ranking_model or WeightedSumModel()

    async def execute(self, request: GenerateRankingCommand) -> RankingResponseDTO:
        """Calcula ranking para sucursales completas y reporta faltantes por separado."""
        basket = self._basket_builder.execute(request.items)
        origin = GeoPoint(
            latitude=request.origin_latitude,
            longitude=request.origin_longitude,
        )
        product_ids = basket.product_ids()
        quantities = {item.product_id: item.quantity for item in basket.items}
        requested_branch_ids = (
            set(request.branch_ids)
            if request.branch_ids is not None
            else None
        )

        async with self._unit_of_work as uow:
            product_names = await self._load_product_names(uow, product_ids)
            missing_products = set(product_ids) - set(product_names)
            if missing_products:
                missing_values = ", ".join(str(product_id) for product_id in missing_products)
                raise ValueError(f"Products not found or inactive: {missing_values}")

            branches = await uow.branches.list_active()
            if requested_branch_ids is not None:
                branches = [branch for branch in branches if branch.id in requested_branch_ids]

            supermarket_names = await self._load_active_supermarket_names(uow, branches)
            branches = [
                branch
                for branch in branches
                if branch.supermarket_id in supermarket_names and branch.active
            ]
            branch_by_id = {branch.id: branch for branch in branches}
            if not branch_by_id:
                return RankingResponseDTO(
                    ranking=[],
                    incomplete_branches=[],
                    observed_at=None,
                    weights=request.weights,
                )

            source_by_id, source_product_ids = await self._load_product_sources(uow, product_ids)
            prices = await uow.prices.find_for_basket(
                product_ids=product_ids,
                branch_ids=list(branch_by_id),
            )
            latest_prices = self._select_latest_valid_prices(
                prices=prices,
                branch_by_id=branch_by_id,
                source_by_id=source_by_id,
                source_product_ids=source_product_ids,
            )

        complete_alternatives: list[Alternative] = []
        incomplete_branches: list[IncompleteBranchDTO] = []
        totals_by_branch: dict[UUID, Decimal] = {}
        observed_at = self._latest_observed_at(latest_prices)

        for branch in branches:
            branch_prices = latest_prices.get(branch.id, {})
            missing_product_ids = [
                product_id
                for product_id in product_ids
                if product_id not in branch_prices
            ]
            branch_dto = self._branch_to_ranking_dto(
                branch=branch,
                supermarket_name=supermarket_names[branch.supermarket_id],
            )
            if missing_product_ids:
                incomplete_branches.append(
                    IncompleteBranchDTO(
                        branch=branch_dto,
                        missing_products=[
                            MissingProductDTO(
                                id=product_id,
                                normalized_name=product_names[product_id],
                            )
                            for product_id in missing_product_ids
                        ],
                    )
                )
                continue

            total_cost = sum(
                (
                    branch_prices[product_id].amount * quantities[product_id]
                    for product_id in product_ids
                ),
                Decimal("0"),
            )
            totals_by_branch[branch.id] = total_cost

        maximum_total = max(totals_by_branch.values(), default=Decimal("0"))
        for branch in branches:
            if branch.id not in totals_by_branch:
                continue

            distance = self._distance_service.calculate(
                origin,
                GeoPoint(latitude=branch.latitude, longitude=branch.longitude),
            )
            complete_alternatives.append(
                Alternative(
                    branch_id=branch.id,
                    supermarket_name=supermarket_names[branch.supermarket_id],
                    branch_name=branch.name,
                    total_cost=totals_by_branch[branch.id],
                    distance_km=distance.kilometers,
                    saving=maximum_total - totals_by_branch[branch.id],
                )
            )

        ranking = (
            self._ranking_model.rank(complete_alternatives, request.weights)
            if complete_alternatives
            else []
        )
        branch_dtos = {
            branch.id: self._branch_to_ranking_dto(
                branch=branch,
                supermarket_name=supermarket_names[branch.supermarket_id],
            )
            for branch in branches
        }
        return RankingResponseDTO(
            ranking=[
                RankingResultDTO(
                    position=result.position,
                    branch=branch_dtos[result.branch_id],
                    total_cost=result.total_cost,
                    distance_km=result.distance_km,
                    saving=result.saving,
                    score=result.score,
                    missing_products_count=result.missing_products_count,
                )
                for result in ranking
            ],
            incomplete_branches=sorted(
                incomplete_branches,
                key=lambda item: (len(item.missing_products), item.branch.supermarket_name, item.branch.name),
            ),
            observed_at=observed_at,
            weights=request.weights,
        )

    @staticmethod
    async def _load_product_names(
        uow: UnitOfWorkPort,
        product_ids: list[UUID],
    ) -> dict[UUID, str]:
        """Obtiene nombres de productos activos solicitados."""
        products = {}
        for product_id in product_ids:
            product = await uow.products.get_by_id(product_id)
            if product is not None and product.active:
                products[product.id] = product.normalized_name
        return products

    @staticmethod
    async def _load_active_supermarket_names(
        uow: UnitOfWorkPort,
        branches: list[Branch],
    ) -> dict[UUID, str]:
        """Obtiene nombres de supermercados activos asociados a sucursales."""
        names: dict[UUID, str] = {}
        for supermarket_id in {branch.supermarket_id for branch in branches}:
            supermarket = await uow.supermarkets.get_by_id(supermarket_id)
            if supermarket is not None and supermarket.active:
                names[supermarket.id] = supermarket.name
        return names

    @staticmethod
    async def _load_product_sources(
        uow: UnitOfWorkPort,
        product_ids: list[UUID],
    ) -> tuple[dict[UUID, ProductSource], dict[UUID, UUID]]:
        """Carga publicaciones activas y permite mapear precio hacia producto."""
        source_by_id = {}
        source_product_ids = {}
        for product_id in product_ids:
            product_sources = await uow.product_sources.find_by_product(product_id)
            for source in product_sources:
                if not source.active:
                    continue
                source_by_id[source.id] = source
                source_product_ids[source.id] = source.product_id
        return source_by_id, source_product_ids

    @staticmethod
    def _select_latest_valid_prices(
        prices: list[Price],
        branch_by_id: dict[UUID, Branch],
        source_by_id: dict[UUID, ProductSource],
        source_product_ids: dict[UUID, UUID],
    ) -> dict[UUID, dict[UUID, Price]]:
        """Selecciona el último precio válido por sucursal y producto."""
        latest: dict[UUID, dict[UUID, Price]] = {}
        for price in prices:
            if not price.available:
                continue

            branch = branch_by_id.get(price.branch_id)
            source = source_by_id.get(price.product_source_id)
            product_id = source_product_ids.get(price.product_source_id)
            if branch is None or source is None or product_id is None:
                continue
            if source.supermarket_id != branch.supermarket_id:
                continue

            current = latest.setdefault(branch.id, {}).get(product_id)
            if current is None or price.observed_at > current.observed_at:
                latest[branch.id][product_id] = price
            elif price.observed_at == current.observed_at and price.amount < current.amount:
                latest[branch.id][product_id] = price
        return latest

    @staticmethod
    def _latest_observed_at(
        prices_by_branch: dict[UUID, dict[UUID, Price]],
    ) -> datetime | None:
        """Obtiene la fecha más reciente usada en el cálculo."""
        observed_values = [
            price.observed_at
            for prices_by_product in prices_by_branch.values()
            for price in prices_by_product.values()
        ]
        return max(observed_values, default=None)

    @staticmethod
    def _branch_to_ranking_dto(
        branch: Branch,
        supermarket_name: str,
    ) -> RankingBranchDTO:
        """Convierte una sucursal en DTO enriquecido para ranking."""
        return RankingBranchDTO(
            id=branch.id,
            supermarket_id=branch.supermarket_id,
            supermarket_name=supermarket_name,
            city_id=branch.city_id,
            name=branch.name,
            address=branch.address,
            latitude=branch.latitude,
            longitude=branch.longitude,
        )
