"""Query object para listar sucursales por supermercado."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListBranchesBySupermarketQuery:
    """Parámetros para consultar sucursales de un supermercado."""

    supermarket_id: UUID
