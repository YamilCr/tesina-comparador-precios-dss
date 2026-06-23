"""Entidad de dominio que relaciona un producto con su publicación externa."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class ProductSource:
    """Representa cómo un supermercado publica un producto normalizado."""

    id: UUID
    product_id: UUID
    supermarket_id: UUID
    original_name: str
    external_code: str | None = None
    product_url: str | None = None
    original_unit: str | None = None
    match_confidence: Decimal | None = None
    active: bool = True

    def __post_init__(self) -> None:
        """Valida el nombre publicado y la confianza de coincidencia opcional."""
        if not self.original_name or not self.original_name.strip():
            raise ValueError("Product source original name cannot be empty.")
        if self.match_confidence is not None and not Decimal("0") <= self.match_confidence <= Decimal("1"):
            raise ValueError("Product source match confidence must be between 0 and 1.")
        self.original_name = self.original_name.strip()

    def activate(self) -> None:
        """Marca la fuente de producto como activa."""
        self.active = True

    def deactivate(self) -> None:
        """Marca la fuente de producto como inactiva."""
        self.active = False
