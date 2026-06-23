"""Entidad de dominio que representa una categoría normalizada de productos."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ProductCategory:
    """Agrupa productos dentro de una jerarquía de categorías opcional."""

    id: UUID
    name: str
    description: str | None = None
    parent_category_id: UUID | None = None
    active: bool = True

    def __post_init__(self) -> None:
        """Valida que la categoría tenga un nombre significativo."""
        if not self.name or not self.name.strip():
            raise ValueError("Product category name cannot be empty.")
        self.name = self.name.strip()

    def activate(self) -> None:
        """Marca la categoría como activa."""
        self.active = True

    def deactivate(self) -> None:
        """Marca la categoría como inactiva."""
        self.active = False
