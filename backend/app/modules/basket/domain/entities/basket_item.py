"""Entidad de dominio no persistida para un ítem de canasta temporal."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class BasketItem:
    """Representa un producto y su cantidad dentro de una canasta temporal."""

    product_id: UUID
    quantity: Decimal

    def __post_init__(self) -> None:
        """Valida que la cantidad solicitada sea positiva."""
        if self.quantity <= Decimal("0"):
            raise ValueError("Basket item quantity must be greater than 0.")
