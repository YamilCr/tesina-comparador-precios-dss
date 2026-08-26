"""Commands for automatic scraping schedule administration."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreateScrapingScheduleCommand:
    source_id: UUID
    name: str
    queries: tuple[str, ...]
    city: str
    interval_minutes: int
    retry_delay_minutes: int = 5
    result_limit: int = 10
    timeout_seconds: int = 60
    next_run_at: datetime | None = None
    enabled: bool = True


@dataclass(frozen=True)
class UpdateScrapingScheduleCommand:
    schedule_id: UUID
    name: str | None = None
    queries: tuple[str, ...] | None = None
    city: str | None = None
    interval_minutes: int | None = None
    retry_delay_minutes: int | None = None
    result_limit: int | None = None
    timeout_seconds: int | None = None
    next_run_at: datetime | None = None
    enabled: bool | None = None

