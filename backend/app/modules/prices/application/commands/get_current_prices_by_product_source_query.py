"""Query object para consultar precios actuales por producto fuente."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetCurrentPricesByProductSourceQuery:
    """Parámetros para consultar precios vigentes de un producto fuente."""

    product_source_id: UUID
