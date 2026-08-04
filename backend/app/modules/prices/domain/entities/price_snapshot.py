"""Entidad de dominio para una vista vigente de precio por sucursal."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class PriceSnapshot:
    """Representa el ultimo precio conocido para un producto en una sucursal."""

    product_id: UUID
    product_source_id: UUID
    branch_id: UUID
    amount: Decimal
    observed_at: datetime
    currency: str = "ARS"
    available: bool = True
    promotion: bool = False

    def __post_init__(self) -> None:
        """Valida los datos minimos de la instantanea."""
        if self.amount < Decimal("0"):
            raise ValueError("Price snapshot amount must be greater than or equal to 0.")
        if not self.currency or not self.currency.strip():
            raise ValueError("Price snapshot currency cannot be empty.")
        self.currency = self.currency.strip()
