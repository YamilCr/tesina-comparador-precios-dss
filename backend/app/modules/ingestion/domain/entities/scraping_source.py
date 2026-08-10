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
    branch_id: UUID | None = None
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

    def update_configuration(
        self,
        *,
        name: str | None = None,
        base_url: str | None = None,
        branch_id: UUID | None = None,
        active: bool | None = None,
    ) -> None:
        """Updates the source configuration while preserving domain validation."""
        if name is not None:
            if not name.strip():
                raise ValueError("Scraping source name cannot be empty.")
            self.name = name.strip()
        if base_url is not None:
            if not base_url.strip():
                raise ValueError("Scraping source base URL cannot be empty.")
            self.base_url = base_url.strip()
        if branch_id is not None:
            self.branch_id = branch_id
        if active is not None:
            self.active = active
