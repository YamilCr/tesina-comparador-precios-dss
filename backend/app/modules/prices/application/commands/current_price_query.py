"""Query object para consultas flexibles de precios actuales."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CurrentPriceQuery:
    """Filtros para consultar precios actuales.

    En application, "precio actual" significa el último precio disponible por
    producto fuente y sucursal. Los filtros de ubicación se resuelven mediante
    puertos del dominio, sin depender de SQLAlchemy ni de FastAPI.
    """

    product_ids: list[UUID] | None = None
    product_source_id: UUID | None = None
    branch_id: UUID | None = None
    city_id: UUID | None = None
    supermarket_id: UUID | None = None
    limit: int = 100

    def __post_init__(self) -> None:
        """Valida que la consulta tenga al menos un filtro coherente."""
        if self.product_ids is not None and not self.product_ids:
            raise ValueError("Current price query requires at least one product.")

        if self.product_source_id is not None and self.product_ids:
            raise ValueError("product_source_id cannot be combined with product_ids.")

        has_any_filter = any(
            (
                bool(self.product_ids),
                self.product_source_id is not None,
                self.branch_id is not None,
                self.city_id is not None,
                self.supermarket_id is not None,
            )
        )
        if not has_any_filter:
            raise ValueError("Current price query requires at least one filter.")

        if self.limit <= 0:
            raise ValueError("Current price query limit must be greater than zero.")

        if self.limit > 500:
            raise ValueError("Current price query limit must be less than or equal to 500.")
