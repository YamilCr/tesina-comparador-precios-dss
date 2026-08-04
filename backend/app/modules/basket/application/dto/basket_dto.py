"""DTOs de aplicación para construir canastas temporales anónimas."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class BasketItemInputDTO:
    """Producto y cantidad solicitados por el usuario anónimo."""

    product_id: UUID
    quantity: Decimal

    def __post_init__(self) -> None:
        """Valida que la cantidad sea positiva."""
        if self.quantity <= Decimal("0"):
            raise ValueError("Basket item quantity must be greater than 0.")


@dataclass(frozen=True)
class BasketItemDTO:
    """Ítem consolidado de una canasta temporal."""

    product_id: UUID
    quantity: Decimal


@dataclass(frozen=True)
class BasketDTO:
    """Resumen de una canasta temporal validada."""

    items: list[BasketItemDTO]
    total_items: int
    product_ids: list[UUID]
