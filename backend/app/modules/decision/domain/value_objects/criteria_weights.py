"""Objeto de valor para los pesos del modelo de decisión multicriterio."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CriteriaWeights:
    """Define los pesos de precio, distancia y ahorro para el ranking."""

    price: Decimal = Decimal("0.6")
    distance: Decimal = Decimal("0.3")
    saving: Decimal = Decimal("0.1")

    def __post_init__(self) -> None:
        """Valida que los pesos sean no negativos y sumen exactamente uno."""
        weights = (self.price, self.distance, self.saving)
        if any(weight < Decimal("0") for weight in weights):
            raise ValueError("Criteria weights must be greater than or equal to 0.")
        if sum(weights, Decimal("0")) != Decimal("1"):
            raise ValueError("Criteria weights must sum to 1.")
