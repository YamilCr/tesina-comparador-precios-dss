"""Entidad de dominio que representa una cadena de supermercados."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Supermarket:
    """Representa un supermercado que puede operar varias sucursales."""

    id: UUID
    name: str
    website_url: str | None = None
    active: bool = True
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida que el supermercado tenga un nombre significativo."""
        if not self.name or not self.name.strip():
            raise ValueError("Supermarket name cannot be empty.")
        self.name = self.name.strip()

    def activate(self) -> None:
        """Marca el supermercado como activo."""
        self.active = True

    def deactivate(self) -> None:
        """Marca el supermercado como inactivo."""
        self.active = False
