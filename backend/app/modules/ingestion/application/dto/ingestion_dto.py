"""DTOs returned by ingestion administration use cases."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.ingestion.domain.entities import ScrapingRun, ScrapingSource


@dataclass(frozen=True)
class ScrapingSourceDTO:
    id: UUID
    supermarket_id: UUID
    name: str
    base_url: str
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
