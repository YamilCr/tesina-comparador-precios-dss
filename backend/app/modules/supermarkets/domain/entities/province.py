"""Entidad de dominio que representa una provincia."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Province:
    """Representa una división provincial dentro de la localización del sistema."""

    id: UUID
    name: str
    iso_code: str | None = None
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida que la provincia tenga un nombre significativo."""
        if not self.name or not self.name.strip():
            raise ValueError("Province name cannot be empty.")
        self.name = self.name.strip()
