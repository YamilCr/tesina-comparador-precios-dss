"""Entidad de dominio no persistida para una canasta temporal."""

from dataclasses import dataclass
from uuid import UUID

from .basket_item import BasketItem


@dataclass
class Basket:
    """Agrupa ítems de una canasta temporal de un usuario anónimo."""

    items: list[BasketItem]

    def __post_init__(self) -> None:
        """Valida que la canasta contenga al menos un ítem."""
        if not self.items:
            raise ValueError("Basket cannot be empty.")

    def total_items(self) -> int:
        """Devuelve la cantidad de líneas de producto de la canasta."""
        return len(self.items)

    def product_ids(self) -> list[UUID]:
        """Devuelve los identificadores de productos incluidos en la canasta."""
        return [item.product_id for item in self.items]

    def is_empty(self) -> bool:
        """Indica si la canasta no contiene ítems."""
        return not self.items
