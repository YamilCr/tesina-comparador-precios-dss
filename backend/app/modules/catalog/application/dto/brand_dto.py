"""DTO de aplicación para marcas del catálogo."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.catalog.domain.entities import Brand


@dataclass(frozen=True)
class BrandDTO:
    """Marca normalizada expuesta por la capa de aplicación."""

    id: UUID
    name: str
    description: str | None = None
    active: bool = True

    @staticmethod
    def from_entity(brand: Brand) -> "BrandDTO":
        """Crea un DTO desde una entidad de dominio Brand."""
        return BrandDTO(
            id=brand.id,
            name=brand.name,
            description=brand.description,
            active=brand.active,
        )
