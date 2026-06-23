"""Entidad de dominio que representa un precio relevado en una sucursal."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass
class Price:
    """Representa el precio observado de un producto fuente en una fecha dada."""

    id: UUID
    product_source_id: UUID
    branch_id: UUID
    amount: Decimal
    observed_at: datetime
    currency: str = "ARS"
    available: bool = True
    promotion: bool = False
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida el importe y la moneda del precio relevado."""
        if self.amount < Decimal("0"):
            raise ValueError("Price amount must be greater than or equal to 0.")
        if not self.currency or not self.currency.strip():
            raise ValueError("Price currency cannot be empty.")
        self.currency = self.currency.strip()

    def mark_unavailable(self) -> None:
        """Marca el precio como no disponible."""
        self.available = False

    def mark_available(self) -> None:
        """Marca el precio como disponible."""
        self.available = True

    def mark_as_promotion(self) -> None:
        """Marca el precio como promocional."""
        self.promotion = True

    def remove_promotion(self) -> None:
        """Quita la marca de promoción del precio."""
        self.promotion = False
