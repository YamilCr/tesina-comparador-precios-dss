"""Query object para consultar historial de precios."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetPriceHistoryQuery:
    """Parámetros para consultar historial de precios."""

    product_source_id: UUID
    branch_id: UUID | None = None
