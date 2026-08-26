"""Repository contract for ingestion source configuration and run audit."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.modules.ingestion.domain.entities import (
    ProductIdentityReview,
    ScheduledRefreshExecution,
    ScrapedProduct,
    ScrapingRun,
    ScrapingSchedule,
    ScrapingSource,
)


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
    async def get_schedule_by_id(self, schedule_id: UUID) -> ScrapingSchedule | None:
        """Returns one automatic refresh schedule by identifier."""

    @abstractmethod
    async def get_schedule_by_source_id(self, source_id: UUID) -> ScrapingSchedule | None:
        """Returns the unique schedule assigned to one source, if configured."""

    @abstractmethod
    async def list_schedules(self, enabled_only: bool | None = None) -> list[ScrapingSchedule]:
        """Lists automatic refresh schedules in deterministic order."""

    @abstractmethod
    async def save_schedule(self, schedule: ScrapingSchedule) -> ScrapingSchedule:
        """Creates or updates one schedule without committing the transaction."""

    @abstractmethod
    async def claim_due_schedules(
        self,
        now: datetime,
        locked_until: datetime,
        limit: int,
    ) -> list[ScrapingSchedule]:
        """Atomically leases due schedules so multiple workers do not duplicate work."""

    @abstractmethod
    async def claim_schedule(
        self,
        schedule_id: UUID,
        now: datetime,
        locked_until: datetime,
    ) -> ScrapingSchedule | None:
        """Attempts to lease one enabled schedule for an immediate execution."""

    @abstractmethod
    async def get_schedule_execution(
        self,
        execution_id: UUID,
    ) -> ScheduledRefreshExecution | None:
        """Returns one scheduler execution by identifier."""

    @abstractmethod
    async def list_schedule_executions(
        self,
        schedule_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ScheduledRefreshExecution]:
        """Lists newest scheduler executions, optionally restricted to one plan."""

    @abstractmethod
    async def save_schedule_execution(
        self,
        execution: ScheduledRefreshExecution,
    ) -> ScheduledRefreshExecution:
        """Creates or updates scheduler history without committing the transaction."""

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

    @abstractmethod
    async def list_loaded_scraped_products(self) -> list[ScrapedProduct]:
        """Lists loaded staging evidence linked to a product publication."""

    @abstractmethod
    async def get_identity_review(self, review_id: UUID) -> ProductIdentityReview | None:
        """Returns one canonical identity review by identifier."""

    @abstractmethod
    async def list_identity_reviews(
        self,
        status: str | None = None,
    ) -> list[ProductIdentityReview]:
        """Lists identity reviews, optionally filtered by decision status."""

    @abstractmethod
    async def save_identity_review(
        self,
        review: ProductIdentityReview,
    ) -> ProductIdentityReview:
        """Creates or updates an auditable canonical identity review."""
