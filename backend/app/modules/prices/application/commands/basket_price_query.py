"""Query object de compatibilidad para consultar precios de una canasta."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class BasketPriceQuery:
    """Consulta de precios para una canasta temporal."""

    product_ids: list[UUID]
    branch_ids: list[UUID] | None = None

    def __post_init__(self) -> None:
        """Valida que haya productos para consultar."""
        if not self.product_ids:
            raise ValueError("Basket price query requires at least one product.")
