"""DTO de aplicación para provincias."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.supermarkets.domain.entities import Province


@dataclass(frozen=True)
class ProvinceDTO:
    """Provincia expuesta por la capa de aplicación."""

    id: UUID
    name: str
    iso_code: str | None = None

    @staticmethod
    def from_entity(province: Province) -> "ProvinceDTO":
        """Crea un DTO desde una entidad de dominio Province."""
        return ProvinceDTO(
            id=province.id,
            name=province.name,
            iso_code=province.iso_code,
        )
