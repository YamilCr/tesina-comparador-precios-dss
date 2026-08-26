"""DTO de aplicación para precios."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.modules.prices.domain.entities import Price


@dataclass(frozen=True)
class PriceDTO:
    """Precio expuesto por la capa de aplicación."""

    id: UUID
    product_source_id: UUID
    branch_id: UUID
    amount: Decimal
    currency: str
    observed_at: datetime
    available: bool = True
    promotion: bool = False
    created_at: datetime | None = None
    quality_status: str = "fresh"
    quality_reason: str | None = None
    age_days: int = 0

    @staticmethod
    def from_entity(
        price: Price,
        *,
        quality_status: str = "fresh",
        quality_reason: str | None = None,
        age_days: int = 0,
    ) -> "PriceDTO":
        """Crea un DTO desde una entidad de dominio Price."""
        return PriceDTO(
            id=price.id,
            product_source_id=price.product_source_id,
            branch_id=price.branch_id,
            amount=price.amount,
            currency=price.currency,
            observed_at=price.observed_at,
            available=price.available,
            promotion=price.promotion,
            created_at=price.created_at,
            quality_status=quality_status,
            quality_reason=quality_reason,
            age_days=age_days,
        )


@dataclass(frozen=True)
class CurrentPriceSelectionDTO:
    """Resultado de precios actuales con métricas de calidad."""

    prices: list[PriceDTO]
    evaluated_at: datetime
    max_age_days: int | None
    eligible_count: int
    stale_excluded_count: int
    suspect_excluded_count: int
