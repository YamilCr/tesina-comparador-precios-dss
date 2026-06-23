"""Objeto de valor para un punto geográfico expresado en coordenadas."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class GeoPoint:
    """Representa una coordenada geográfica sin asociarla a persistencia."""

    latitude: Decimal
    longitude: Decimal

    def __post_init__(self) -> None:
        """Valida que las coordenadas pertenezcan a sus rangos geográficos."""
        if not Decimal("-90") <= self.latitude <= Decimal("90"):
            raise ValueError("Geo point latitude must be between -90 and 90.")
        if not Decimal("-180") <= self.longitude <= Decimal("180"):
            raise ValueError("Geo point longitude must be between -180 and 180.")
