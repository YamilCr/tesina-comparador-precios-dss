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

    @staticmethod
    def from_entity(price: Price) -> "PriceDTO":
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
        )
