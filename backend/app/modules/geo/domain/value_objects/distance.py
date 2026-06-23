"""Objeto de valor para una distancia geográfica."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Distance:
    """Representa una distancia no negativa expresada en kilómetros."""

    kilometers: Decimal

    def __post_init__(self) -> None:
        """Valida que la distancia no sea negativa."""
        if self.kilometers < Decimal("0"):
            raise ValueError("Distance kilometers must be greater than or equal to 0.")

    def meters(self) -> Decimal:
        """Convierte la distancia a metros."""
        return self.kilometers * Decimal("1000")
