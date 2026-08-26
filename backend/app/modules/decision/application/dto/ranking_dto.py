"""DTOs de aplicación para solicitar y devolver rankings DSS."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.decision.application.commands import GenerateRankingCommand
from app.modules.decision.domain.value_objects import CriteriaWeights


RankingRequestDTO = GenerateRankingCommand


@dataclass(frozen=True)
class RankingBranchDTO:
    """Sucursal candidata dentro de una respuesta de ranking."""

    id: UUID
    supermarket_id: UUID
    supermarket_name: str
    city_id: UUID
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal


@dataclass(frozen=True)
class MissingProductDTO:
    """Producto que no pudo cubrirse en una sucursal."""

    id: UUID
    normalized_name: str
    reason: str = "missing"


@dataclass(frozen=True)
class IncompleteBranchDTO:
    """Sucursal excluida del ranking por no cubrir toda la canasta."""

    branch: RankingBranchDTO
    missing_products: list[MissingProductDTO]


@dataclass(frozen=True)
class RankingResultDTO:
    """Resultado rankeado para una sucursal completa."""

    position: int
    branch: RankingBranchDTO
    total_cost: Decimal
    distance_km: Decimal
    saving: Decimal
    score: Decimal
    missing_products_count: int = 0


@dataclass(frozen=True)
class RankingQualityDTO:
    """Métricas de calidad aplicadas antes de calcular el ranking."""

    evaluated_at: datetime
    max_price_age_days: int
    eligible_price_count: int
    stale_excluded_count: int
    suspect_excluded_count: int


@dataclass(frozen=True)
class RankingResponseDTO:
    """Respuesta completa del cálculo DSS en memoria."""

    ranking: list[RankingResultDTO]
    incomplete_branches: list[IncompleteBranchDTO]
    observed_at: datetime | None
    weights: CriteriaWeights
    quality: RankingQualityDTO
