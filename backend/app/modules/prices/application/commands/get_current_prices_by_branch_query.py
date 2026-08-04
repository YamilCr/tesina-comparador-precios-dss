"""Query object para consultar precios actuales por sucursal."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetCurrentPricesByBranchQuery:
    """Parámetros para consultar precios vigentes de una sucursal."""

    branch_id: UUID
