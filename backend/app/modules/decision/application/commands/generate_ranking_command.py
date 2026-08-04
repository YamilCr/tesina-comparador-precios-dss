"""Command de aplicación para solicitar un ranking DSS multicriterio."""

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.basket.application.dto import BasketItemInputDTO
from app.modules.decision.domain.value_objects import CriteriaWeights


@dataclass(frozen=True)
class GenerateRankingCommand:
    """Solicitud de cálculo de ranking para una canasta temporal."""

    items: list[BasketItemInputDTO]
    origin_latitude: Decimal
    origin_longitude: Decimal
    branch_ids: list[UUID] | None = None
    weights: CriteriaWeights = field(default_factory=CriteriaWeights)

    def __post_init__(self) -> None:
        """Valida canasta, coordenadas y sucursales opcionales."""
        if not self.items:
            raise ValueError("Generate ranking command requires at least one basket item.")
        if not Decimal("-90") <= self.origin_latitude <= Decimal("90"):
            raise ValueError("Origin latitude must be between -90 and 90.")
        if not Decimal("-180") <= self.origin_longitude <= Decimal("180"):
            raise ValueError("Origin longitude must be between -180 and 180.")
        if self.branch_ids is not None and len(self.branch_ids) != len(set(self.branch_ids)):
            raise ValueError("Branch ids cannot contain duplicates.")
