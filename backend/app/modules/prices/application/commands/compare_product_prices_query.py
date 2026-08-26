"""Query object para comparar precios actuales por productos normalizados."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CompareProductPricesQuery:
    """Parámetros para comparar precios actuales de productos.

    Los filtros de ubicación son opcionales y se resuelven en application.
    """

    product_ids: list[UUID]
    branch_id: UUID | None = None
    city_id: UUID | None = None
    supermarket_id: UUID | None = None
    limit: int = 100
    as_of: datetime | None = None
    max_age_days: int | None = None

    def __post_init__(self) -> None:
        """Valida que se haya solicitado al menos un producto y un límite válido."""
        if not self.product_ids:
            raise ValueError("Compare product prices query requires at least one product.")

        if self.limit <= 0:
            raise ValueError("Compare product prices query limit must be greater than zero.")

        if self.limit > 500:
            raise ValueError("Compare product prices query limit must be less than or equal to 500.")

        if self.max_age_days is not None and self.max_age_days <= 0:
            raise ValueError("Maximum price age must be greater than zero.")
