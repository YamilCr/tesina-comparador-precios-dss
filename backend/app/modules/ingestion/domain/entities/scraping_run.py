"""Entidad de dominio para auditar una corrida de scraping."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


VALID_SCRAPING_RUN_STATUSES = frozenset({"pending", "running", "succeeded", "failed"})


@dataclass
class ScrapingRun:
    """Registra el ciclo de vida de una ejecucion de scraping."""

    id: UUID
    scraping_source_id: UUID
    started_at: datetime
    status: str = "pending"
    finished_at: datetime | None = None
    items_scraped: int = 0
    items_loaded: int = 0
    error_message: str | None = None

    def __post_init__(self) -> None:
        """Valida estado, contadores y orden temporal."""
        if self.status not in VALID_SCRAPING_RUN_STATUSES:
            raise ValueError(f"Invalid scraping run status: {self.status}.")
        if self.items_scraped < 0 or self.items_loaded < 0:
            raise ValueError("Scraping run counters cannot be negative.")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("Scraping run finished_at cannot be before started_at.")
        if self.error_message is not None:
            self.error_message = self.error_message.strip() or None

    def mark_running(self) -> None:
        """Marca la corrida como iniciada."""
        self.status = "running"

    def mark_succeeded(
        self,
        finished_at: datetime,
        items_scraped: int,
        items_loaded: int,
    ) -> None:
        """Marca la corrida como exitosa."""
        if items_scraped < 0 or items_loaded < 0:
            raise ValueError("Scraping run counters cannot be negative.")
        if finished_at < self.started_at:
            raise ValueError("Scraping run finished_at cannot be before started_at.")
        self.status = "succeeded"
        self.finished_at = finished_at
        self.items_scraped = items_scraped
        self.items_loaded = items_loaded
        self.error_message = None

    def mark_failed(self, finished_at: datetime, error_message: str) -> None:
        """Marca la corrida como fallida con un mensaje de error."""
        if finished_at < self.started_at:
            raise ValueError("Scraping run finished_at cannot be before started_at.")
        if not error_message or not error_message.strip():
            raise ValueError("Scraping run error message cannot be empty.")
        self.status = "failed"
        self.finished_at = finished_at
        self.error_message = error_message.strip()
