"""Entidad de dominio que representa una sucursal física."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class Branch:
    """Representa una sucursal de un supermercado ubicada en una ciudad."""

    id: UUID
    supermarket_id: UUID
    city_id: UUID
    name: str
    address: str
    latitude: Decimal
    longitude: Decimal
    active: bool = True

    def __post_init__(self) -> None:
        """Valida los datos mínimos y las coordenadas de la sucursal."""
        if not self.name or not self.name.strip():
            raise ValueError("Branch name cannot be empty.")
        if not self.address or not self.address.strip():
            raise ValueError("Branch address cannot be empty.")
        if not Decimal("-90") <= self.latitude <= Decimal("90"):
            raise ValueError("Branch latitude must be between -90 and 90.")
        if not Decimal("-180") <= self.longitude <= Decimal("180"):
            raise ValueError("Branch longitude must be between -180 and 180.")
        self.name = self.name.strip()
        self.address = self.address.strip()

    def activate(self) -> None:
        """Marca la sucursal como activa."""
        self.active = True

    def deactivate(self) -> None:
        """Marca la sucursal como inactiva."""
        self.active = False
