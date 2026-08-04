"""DTO de aplicación para supermercados."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.supermarkets.domain.entities import Supermarket


@dataclass(frozen=True)
class SupermarketDTO:
    """Supermercado expuesto por la capa de aplicación."""

    id: UUID
    name: str
    website_url: str | None = None
    active: bool = True

    @staticmethod
    def from_entity(supermarket: Supermarket) -> "SupermarketDTO":
        """Crea un DTO desde una entidad de dominio Supermarket."""
        return SupermarketDTO(
            id=supermarket.id,
            name=supermarket.name,
            website_url=supermarket.website_url,
            active=supermarket.active,
        )
