"""Entidad de dominio que representa una ciudad."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class City:
    """Representa una ciudad asociada a una provincia."""

    id: UUID
    province_id: UUID
    name: str
    postal_code: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    def __post_init__(self) -> None:
        """Valida el nombre y las coordenadas opcionales de la ciudad."""
        if not self.name or not self.name.strip():
            raise ValueError("City name cannot be empty.")
        if self.latitude is not None and not Decimal("-90") <= self.latitude <= Decimal("90"):
            raise ValueError("City latitude must be between -90 and 90.")
        if self.longitude is not None and not Decimal("-180") <= self.longitude <= Decimal("180"):
            raise ValueError("City longitude must be between -180 and 180.")
        self.name = self.name.strip()
