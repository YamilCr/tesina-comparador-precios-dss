"""Repository contract for ingestion source configuration and run audit."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.ingestion.domain.entities import ScrapedProduct, ScrapingRun, ScrapingSource


class IngestionRepositoryPort(ABC):
    """Defines persistence operations required by ingestion administration."""

    @abstractmethod
    async def get_source_by_id(self, source_id: UUID) -> ScrapingSource | None:
        """Returns one configured scraping source by identifier."""

    @abstractmethod
    async def get_source_by_supermarket_and_name(
        self,
        supermarket_id: UUID,
        name: str,
    ) -> ScrapingSource | None:
        """Returns a source with the same supermarket and display name."""

    @abstractmethod
    async def list_sources(self, active_only: bool | None = None) -> list[ScrapingSource]:
        """Lists configured sources, optionally restricted by their active state."""

    @abstractmethod
    async def save_source(self, source: ScrapingSource) -> ScrapingSource:
        """Creates or updates a source without committing the transaction."""

    @abstractmethod
    async def get_run_by_id(self, run_id: UUID) -> ScrapingRun | None:
        """Returns one scraping run by identifier."""

    @abstractmethod
    async def list_runs(
        self,
        source_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScrapingRun]:
        """Lists newest runs first, optionally for one source."""

    @abstractmethod
    async def find_open_run(self, source_id: UUID) -> ScrapingRun | None:
        """Returns the pending or running audit record for a source, if any."""

    @abstractmethod
    async def save_run(self, run: ScrapingRun) -> ScrapingRun:
        """Creates or updates a run without committing the transaction."""

    @abstractmethod
    async def save_scraped_products(
        self,
        products: list[ScrapedProduct],
    ) -> list[ScrapedProduct]:
        """Stores raw extracted products and their ETL processing result."""

    @abstractmethod
    async def list_scraped_products(
        self,
        run_id: UUID,
        statuses: set[str] | None = None,
    ) -> list[ScrapedProduct]:
        """Lists raw products for one run, optionally filtered by processing status."""
