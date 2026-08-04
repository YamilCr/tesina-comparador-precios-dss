"""Entidad de dominio para una fuente externa de scraping."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ScrapingSource:
    """Describe una fuente de extraccion asociada a un supermercado."""

    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
    active: bool = True
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        """Valida nombre y URL base de la fuente."""
        if not self.name or not self.name.strip():
            raise ValueError("Scraping source name cannot be empty.")
        if not self.base_url or not self.base_url.strip():
            raise ValueError("Scraping source base URL cannot be empty.")
        self.name = self.name.strip()
        self.base_url = self.base_url.strip()

    def activate(self) -> None:
        """Marca la fuente como activa."""
        self.active = True

    def deactivate(self) -> None:
        """Marca la fuente como inactiva."""
        self.active = False
