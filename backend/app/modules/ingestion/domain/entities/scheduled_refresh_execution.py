"""Domain entity for one scheduled refresh audit record."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


VALID_SCHEDULE_EXECUTION_STATUSES = frozenset({"running", "succeeded", "failed"})


@dataclass
class ScheduledRefreshExecution:
    """Tracks one scheduler trigger and its optional source scraping run."""

    id: UUID
    schedule_id: UUID
    scheduled_for: datetime
    started_at: datetime
    status: str = "running"
    scraping_run_id: UUID | None = None
    finished_at: datetime | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in VALID_SCHEDULE_EXECUTION_STATUSES:
            raise ValueError(f"Invalid schedule execution status: {self.status}.")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("Schedule execution cannot finish before it starts.")
        if self.error_message is not None:
            self.error_message = self.error_message.strip() or None

    def mark_succeeded(self, finished_at: datetime, scraping_run_id: UUID) -> None:
        if self.status != "running":
            raise ValueError("Only running schedule executions can succeed.")
        if finished_at < self.started_at:
            raise ValueError("Schedule execution cannot finish before it starts.")
        self.status = "succeeded"
        self.scraping_run_id = scraping_run_id
        self.finished_at = finished_at
        self.error_message = None

    def mark_failed(
        self,
        finished_at: datetime,
        error_message: str,
        scraping_run_id: UUID | None = None,
    ) -> None:
        if self.status != "running":
            raise ValueError("Only running schedule executions can fail.")
        if finished_at < self.started_at:
            raise ValueError("Schedule execution cannot finish before it starts.")
        message = error_message.strip()
        if not message:
            raise ValueError("Schedule execution error message cannot be empty.")
        self.status = "failed"
        self.scraping_run_id = scraping_run_id
        self.finished_at = finished_at
        self.error_message = message[:2000]

