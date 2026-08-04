"""Query object de compatibilidad para listar sucursales con filtros opcionales."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListBranchesQuery:
    """Filtros opcionales para listar sucursales activas."""

    city_id: UUID | None = None
    supermarket_id: UUID | None = None
    active_only: bool = True
