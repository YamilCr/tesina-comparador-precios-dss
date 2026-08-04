"""DTO de aplicación para ciudades."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.modules.supermarkets.domain.entities import City


@dataclass(frozen=True)
class CityDTO:
    """Ciudad expuesta por la capa de aplicación."""

    id: UUID
    province_id: UUID
    name: str
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    @staticmethod
    def from_entity(city: City) -> "CityDTO":
        """Crea un DTO desde una entidad de dominio City."""
        return CityDTO(
            id=city.id,
            province_id=city.province_id,
            name=city.name,
            postal_code=city.postal_code,
            latitude=city.latitude,
            longitude=city.longitude,
        )
