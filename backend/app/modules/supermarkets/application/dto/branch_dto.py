"""DTO de aplicación para sucursales."""

from dataclasses import dataclass
from datetime import datetime
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
    coordinates_verified: bool = True
    coordinate_source: str | None = None
    coordinates_verified_at: datetime | None = None

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
            coordinates_verified=branch.coordinates_verified,
            coordinate_source=branch.coordinate_source,
            coordinates_verified_at=branch.coordinates_verified_at,
        )
