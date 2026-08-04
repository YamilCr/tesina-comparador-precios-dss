"""Query object para listar sucursales por ciudad."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListBranchesByCityQuery:
    """Parámetros para consultar sucursales de una ciudad."""

    city_id: UUID
