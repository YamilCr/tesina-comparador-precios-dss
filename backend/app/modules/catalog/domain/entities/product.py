"""Entidad de dominio que representa un producto normalizado."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class Product:
    """Representa un producto canónico independiente de un supermercado."""

    id: UUID
    normalized_name: str
    category_id: UUID | None = None
    brand_id: UUID | None = None
    description: str | None = None
    unit_measure: str | None = None
    net_content: Decimal | None = None
    internal_code: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        """Valida el nombre normalizado y el contenido neto opcional."""
        if not self.normalized_name or not self.normalized_name.strip():
            raise ValueError("Product normalized name cannot be empty.")
        if self.net_content is not None and self.net_content <= Decimal("0"):
            raise ValueError("Product net content must be greater than 0.")
        self.normalized_name = self.normalized_name.strip()

    def activate(self) -> None:
        """Marca el producto como activo."""
        self.active = True

    def deactivate(self) -> None:
        """Marca el producto como inactivo."""
        self.active = False
