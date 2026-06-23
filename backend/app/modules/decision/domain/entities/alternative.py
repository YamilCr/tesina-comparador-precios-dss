"""Entidad de dominio no persistida para una alternativa de compra."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class Alternative:
    """Representa una sucursal candidata dentro de un cálculo de decisión."""

    branch_id: UUID
    supermarket_name: str
    branch_name: str
    total_cost: Decimal
    distance_km: Decimal
    saving: Decimal
    missing_products_count: int = 0

    def __post_init__(self) -> None:
        """Valida los datos usados como criterios de decisión."""
        if not self.supermarket_name or not self.supermarket_name.strip():
            raise ValueError("Alternative supermarket name cannot be empty.")
        if not self.branch_name or not self.branch_name.strip():
            raise ValueError("Alternative branch name cannot be empty.")
        if self.total_cost < Decimal("0"):
            raise ValueError("Alternative total cost must be greater than or equal to 0.")
        if self.distance_km < Decimal("0"):
            raise ValueError("Alternative distance must be greater than or equal to 0.")
        if self.saving < Decimal("0"):
            raise ValueError("Alternative saving must be greater than or equal to 0.")
        if self.missing_products_count < 0:
            raise ValueError("Alternative missing products count must be greater than or equal to 0.")
        self.supermarket_name = self.supermarket_name.strip()
        self.branch_name = self.branch_name.strip()
