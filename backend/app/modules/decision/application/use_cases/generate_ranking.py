"""Caso de uso para generar ranking DSS multicriterio en memoria."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.modules.basket.application.use_cases.build_basket import BuildBasketUseCase
from app.modules.decision.application.commands import GenerateRankingCommand
from app.modules.decision.application.branch_prices import load_branch_prices
from app.modules.decision.application.substitutions import (
    InvalidSubstitution,
    candidate_payload,
    validate_substitutions,
)
from app.modules.decision.application.dto.ranking_dto import (
    IncompleteBranchDTO,
    MissingProductDTO,
    RankingBranchDTO,
    RankingQualityDTO,
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
        evaluated_at = request.as_of or datetime.now(timezone.utc)
        requested_branch_ids = set(request.branch_ids) if request.branch_ids is not None else None

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
                if branch.supermarket_id in supermarket_names
                and branch.active
                and branch.coordinates_verified
            ]
            branch_by_id = {branch.id: branch for branch in branches}
            replacements = await validate_substitutions(
                uow,
                request.substitutions,
                product_ids,
                branch_by_id,
            )
            if not branch_by_id:
                return RankingResponseDTO(
                    ranking=[],
                    incomplete_branches=[],
                    observed_at=None,
                    weights=request.weights,
                    quality=RankingQualityDTO(
                        evaluated_at=evaluated_at,
                        max_price_age_days=request.max_price_age_days,
                        eligible_price_count=0,
                        stale_excluded_count=0,
                        suspect_excluded_count=0,
                    ),
                )

            effective_ids = set(product_ids) | {p.id for p, _ in replacements.values()}
            pricing = await load_branch_prices(
                uow,
                list(effective_ids),
                branch_by_id,
                evaluated_at,
                request.max_price_age_days,
            )
            latest_prices, quality_selection, exclusion_reasons = (
                pricing.selected,
                pricing.quality,
                pricing.reasons,
            )
            details_by_branch: dict[UUID, list[dict]] = {}
            for (branch_id, original_id), (replacement, brands) in replacements.items():
                price = latest_prices.get(branch_id, {}).get(replacement.id)
                if price is None:
                    raise InvalidSubstitution(
                        branch_id,
                        original_id,
                        "El reemplazo ya no tiene un precio apto en esta cadena.",
                    )
                detail = candidate_payload(
                    original_id, replacement, price, quantities[original_id], branch_id, brands
                )
                detail["original_name"] = product_names[original_id]
                details_by_branch.setdefault(branch_id, []).append(detail)

        def effective_product(branch_id, product_id):
            replacement = replacements.get((branch_id, product_id))
            return replacement[0].id if replacement else product_id

        complete_alternatives: list[Alternative] = []
        incomplete_branches: list[IncompleteBranchDTO] = []
        totals_by_branch: dict[UUID, Decimal] = {}
        observed_at = self._latest_observed_at(latest_prices)

        for branch in branches:
            branch_prices = latest_prices.get(branch.id, {})
            missing_product_ids = [
                product_id
                for product_id in product_ids
                if effective_product(branch.id, product_id) not in branch_prices
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
                                reason=exclusion_reasons.get(
                                    (branch.id, product_id),
                                    "missing",
                                ),
                            )
                            for product_id in missing_product_ids
                        ],
                        distance_km=self._distance_service.calculate(
                            origin,
                            GeoPoint(latitude=branch.latitude, longitude=branch.longitude),
                        ).kilometers,
                        covered_products_count=len(product_ids) - len(missing_product_ids),
                        total_products_count=len(product_ids),
                        substitutions=details_by_branch.get(branch.id, []),
                    )
                )
                continue

            total_cost = sum(
                (
                    branch_prices[effective_product(branch.id, product_id)].amount
                    * quantities[product_id]
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
                    basket_type="substituted"
                    if result.branch_id in details_by_branch
                    else "original",
                    substitutions=details_by_branch.get(result.branch_id, []),
                )
                for result in ranking
            ],
            incomplete_branches=sorted(
                incomplete_branches,
                key=lambda item: (
                    len(item.missing_products),
                    item.distance_km,
                    str(item.branch.id),
                ),
            ),
            observed_at=observed_at,
            weights=request.weights,
            quality=RankingQualityDTO(
                evaluated_at=evaluated_at,
                max_price_age_days=request.max_price_age_days,
                eligible_price_count=len(quality_selection.eligible),
                stale_excluded_count=len(quality_selection.stale),
                suspect_excluded_count=len(quality_selection.suspect),
            ),
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
