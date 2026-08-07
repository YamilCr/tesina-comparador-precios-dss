"""Commands for the lifecycle of scraping audit runs."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class StartScrapingRunCommand:
    source_id: UUID


@dataclass(frozen=True)
class CompleteScrapingRunCommand:
    run_id: UUID
    items_scraped: int
    items_loaded: int


@dataclass(frozen=True)
class FailScrapingRunCommand:
    run_id: UUID
    error_message: str
