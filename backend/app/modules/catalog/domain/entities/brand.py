"""Entidad de dominio que representa una marca de producto."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class Brand:
    """Representa una marca normalizada dentro del catálogo."""

    id: UUID
    name: str
    description: str | None = None
    active: bool = True

    def __post_init__(self) -> None:
        """Valida que la marca tenga un nombre significativo."""
        if not self.name or not self.name.strip():
            raise ValueError("Brand name cannot be empty.")
        self.name = self.name.strip()

    def activate(self) -> None:
        """Marca la marca como activa."""
        self.active = True

    def deactivate(self) -> None:
        """Marca la marca como inactiva."""
        self.active = False
