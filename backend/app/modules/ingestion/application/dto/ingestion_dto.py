"""DTOs returned by ingestion administration use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.ingestion.domain.entities import (
    ScheduledRefreshExecution,
    ScrapingRun,
    ScrapingSchedule,
    ScrapingSource,
)


@dataclass(frozen=True)
class ScrapingSourceDTO:
    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
    scraper_key: str
    branch_id: UUID | None
    active: bool
    created_at: datetime | None

    @classmethod
    def from_entity(cls, source: ScrapingSource) -> "ScrapingSourceDTO":
        return cls(
            id=source.id,
            supermarket_id=source.supermarket_id,
            name=source.name,
            base_url=source.base_url,
            scraper_key=source.scraper_key,
            branch_id=source.branch_id,
            active=source.active,
            created_at=source.created_at,
        )


@dataclass(frozen=True)
class ScrapingRunDTO:
    id: UUID
    scraping_source_id: UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    items_scraped: int
    items_loaded: int
    error_message: str | None

    @classmethod
    def from_entity(cls, run: ScrapingRun) -> "ScrapingRunDTO":
        return cls(
            id=run.id,
            scraping_source_id=run.scraping_source_id,
            status=run.status,
            started_at=run.started_at,
            finished_at=run.finished_at,
            items_scraped=run.items_scraped,
            items_loaded=run.items_loaded,
            error_message=run.error_message,
        )


@dataclass(frozen=True)
class ScrapingScheduleDTO:
    id: UUID
    scraping_source_id: UUID
    name: str
    queries: tuple[str, ...]
    city: str
    interval_minutes: int
    retry_delay_minutes: int
    result_limit: int
    timeout_seconds: int
    enabled: bool
    next_run_at: datetime
    locked_until: datetime | None
    consecutive_failures: int
    created_at: datetime | None
    updated_at: datetime | None

    @classmethod
    def from_entity(cls, schedule: ScrapingSchedule) -> "ScrapingScheduleDTO":
        return cls(
            id=schedule.id,
            scraping_source_id=schedule.scraping_source_id,
            name=schedule.name,
            queries=schedule.queries,
            city=schedule.city,
            interval_minutes=schedule.interval_minutes,
            retry_delay_minutes=schedule.retry_delay_minutes,
            result_limit=schedule.result_limit,
            timeout_seconds=schedule.timeout_seconds,
            enabled=schedule.enabled,
            next_run_at=schedule.next_run_at,
            locked_until=schedule.locked_until,
            consecutive_failures=schedule.consecutive_failures,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )


@dataclass(frozen=True)
class ScheduledRefreshExecutionDTO:
    id: UUID
    schedule_id: UUID
    scraping_run_id: UUID | None
    status: str
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None

    @classmethod
    def from_entity(
        cls,
        execution: ScheduledRefreshExecution,
    ) -> "ScheduledRefreshExecutionDTO":
        return cls(
            id=execution.id,
            schedule_id=execution.schedule_id,
            scraping_run_id=execution.scraping_run_id,
            status=execution.status,
            scheduled_for=execution.scheduled_for,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            error_message=execution.error_message,
        )


@dataclass(frozen=True)
class ScrapingExecutionDTO:
    """Reports the audited result of an extraction without loading it into the catalog."""

    run: ScrapingRunDTO
    items: list[dict]


@dataclass(frozen=True)
class ScrapingRefreshDTO:
    """Reports a complete extraction and ETL refresh for one configured source."""

    run: ScrapingRunDTO
    load: "EtlLoadResultDTO"


@dataclass(frozen=True)
class ConcurrentScrapingSourceResultDTO:
    """Reports one source outcome from a multi-source concurrent refresh."""

    source_id: UUID
    source_name: str
    run: ScrapingRunDTO
    duration_ms: int
    load: "EtlLoadResultDTO | None" = None
    error_message: str | None = None


@dataclass(frozen=True)
class ConcurrentScrapingRefreshDTO:
    """Collects partial outcomes from a bounded multi-source refresh."""

    results: list[ConcurrentScrapingSourceResultDTO]


@dataclass(frozen=True)
class ScrapingBenchmarkSourceDTO:
    """Captures one source outcome measured during an experimental run."""

    source_id: UUID
    source_name: str
    run: ScrapingRunDTO | None
    load: "EtlLoadResultDTO | None" = None
    error_message: str | None = None


@dataclass(frozen=True)
class ScrapingBenchmarkDTO:
    """Captures comparable end-to-end metrics for one benchmark iteration."""

    mode: str
    duration_ms: int
    sources: list[ScrapingBenchmarkSourceDTO]


@dataclass(frozen=True)
class EtlLoadResultDTO:
    """Summarizes a repeatable ETL pass over one successful scraping run."""

    run_id: UUID
    processed: int
    loaded: int
    rejected: int
    duplicates: int
    unmatched: int
    created_products: int
    created_prices: int
