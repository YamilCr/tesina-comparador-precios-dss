"""DTO de aplicación para sucursales."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.supermarkets.domain.entities import Branch


@dataclass(frozen=True)
class BranchDTO:
    """Sucursal física expuesta por la capa de aplicación."""

    id: UUID
    supermarket_id: UUID
    city_id: UUID
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    active: bool = True

    @staticmethod
    def from_entity(branch: Branch) -> "BranchDTO":
        """Crea un DTO desde una entidad de dominio Branch."""
        return BranchDTO(
            id=branch.id,
            supermarket_id=branch.supermarket_id,
            city_id=branch.city_id,
            name=branch.name,
            address=branch.address,
            latitude=branch.latitude,
            longitude=branch.longitude,
            active=branch.active,
        )
