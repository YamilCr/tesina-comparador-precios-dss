"""Domain entity for an automatic scraping refresh schedule."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID


@dataclass
class ScrapingSchedule:
    """Defines when and how one configured source is refreshed."""

    id: UUID
    scraping_source_id: UUID
    name: str
    queries: tuple[str, ...]
    city: str
    interval_minutes: int
    retry_delay_minutes: int
    result_limit: int
    timeout_seconds: int
    next_run_at: datetime
    enabled: bool = True
    locked_until: datetime | None = None
    consecutive_failures: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()
        self.city = self.city.strip()
        self.queries = self._normalize_queries(self.queries)
        if not self.name:
            raise ValueError("Scraping schedule name cannot be empty.")
        if not self.city:
            raise ValueError("Scraping schedule city cannot be empty.")
        if not 1 <= self.interval_minutes <= 10080:
            raise ValueError("Scraping schedule interval must be between 1 and 10080 minutes.")
        if not 1 <= self.retry_delay_minutes <= 1440:
            raise ValueError("Scraping schedule retry delay must be between 1 and 1440 minutes.")
        if not 1 <= self.result_limit <= 20:
            raise ValueError("Scraping schedule result limit must be between 1 and 20.")
        if not 1 <= self.timeout_seconds <= 300:
            raise ValueError("Scraping schedule timeout must be between 1 and 300 seconds.")
        if self.consecutive_failures < 0:
            raise ValueError("Scraping schedule failure count cannot be negative.")

    @staticmethod
    def _normalize_queries(queries: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(dict.fromkeys(query.strip() for query in queries if query.strip()))
        if not 1 <= len(normalized) <= 5:
            raise ValueError("Scraping schedule requires between one and five queries.")
        return normalized

    def update_configuration(
        self,
        *,
        name: str | None = None,
        queries: tuple[str, ...] | None = None,
        city: str | None = None,
        interval_minutes: int | None = None,
        retry_delay_minutes: int | None = None,
        result_limit: int | None = None,
        timeout_seconds: int | None = None,
        next_run_at: datetime | None = None,
        enabled: bool | None = None,
    ) -> None:
        """Updates administrative values and applies all domain validation again."""
        candidate = ScrapingSchedule(
            id=self.id,
            scraping_source_id=self.scraping_source_id,
            name=self.name if name is None else name,
            queries=self.queries if queries is None else queries,
            city=self.city if city is None else city,
            interval_minutes=(
                self.interval_minutes if interval_minutes is None else interval_minutes
            ),
            retry_delay_minutes=(
                self.retry_delay_minutes
                if retry_delay_minutes is None
                else retry_delay_minutes
            ),
            result_limit=self.result_limit if result_limit is None else result_limit,
            timeout_seconds=(
                self.timeout_seconds if timeout_seconds is None else timeout_seconds
            ),
            next_run_at=self.next_run_at if next_run_at is None else next_run_at,
            enabled=self.enabled if enabled is None else enabled,
            locked_until=self.locked_until,
            consecutive_failures=self.consecutive_failures,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
        self.name = candidate.name
        self.queries = candidate.queries
        self.city = candidate.city
        self.interval_minutes = candidate.interval_minutes
        self.retry_delay_minutes = candidate.retry_delay_minutes
        self.result_limit = candidate.result_limit
        self.timeout_seconds = candidate.timeout_seconds
        self.next_run_at = candidate.next_run_at
        self.enabled = candidate.enabled

    def mark_succeeded(self, finished_at: datetime) -> None:
        """Schedules the regular interval after a successful refresh."""
        self.consecutive_failures = 0
        self.locked_until = None
        self.next_run_at = finished_at + timedelta(minutes=self.interval_minutes)
        self.updated_at = finished_at

    def mark_failed(self, finished_at: datetime) -> None:
        """Releases the lease and applies bounded exponential retry backoff."""
        self.consecutive_failures += 1
        multiplier = 2 ** min(self.consecutive_failures - 1, 3)
        retry_minutes = min(self.retry_delay_minutes * multiplier, self.interval_minutes)
        self.locked_until = None
        self.next_run_at = finished_at + timedelta(minutes=retry_minutes)
        self.updated_at = finished_at
