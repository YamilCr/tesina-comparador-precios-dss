"""Executes one leased schedule through the existing audited refresh pipeline."""

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.ingestion.application.dto import ScheduledRefreshExecutionDTO
from app.modules.ingestion.domain.entities import (
    ScheduledRefreshExecution,
    ScrapingSchedule,
    ScrapingSource,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.application import UnitOfWorkPort

from .concurrent_refresh_scraping_sources import ConcurrentRefreshScrapingSourcesUseCase


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RunScrapingScheduleUseCase:
    """Records scheduler history and isolates extraction or ETL failures."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        scraper_factory: Callable[[ScrapingSource, ScrapingSchedule], ScraperPort],
        now_provider: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._scraper_factory = scraper_factory
        self._now_provider = now_provider

    async def execute(
        self,
        schedule_id: UUID,
        *,
        scheduled_for: datetime,
    ) -> ScheduledRefreshExecutionDTO:
        started_at = self._now_provider()
        schedule = await self._load_schedule(schedule_id)
        execution = ScheduledRefreshExecution(
            id=uuid4(),
            schedule_id=schedule.id,
            scheduled_for=scheduled_for,
            started_at=started_at,
        )
        async with self._unit_of_work as uow:
            saved_execution = await uow.ingestion.save_schedule_execution(execution)
            await uow.commit()

        scraping_run_id: UUID | None = None
        error_message: str | None = None
        try:
            refresh = await ConcurrentRefreshScrapingSourcesUseCase(
                self._unit_of_work,
                lambda source: self._scraper_factory(source, schedule),
                max_concurrency=1,
                timeout_seconds=schedule.timeout_seconds,
            ).execute([schedule.scraping_source_id])
            result = refresh.results[0]
            scraping_run_id = result.run.id
            error_message = result.error_message
        except Exception as error:
            error_message = self._format_error(error)

        finished_at = self._now_provider()
        async with self._unit_of_work as uow:
            current_schedule = await uow.ingestion.get_schedule_by_id(schedule.id)
            current_execution = await uow.ingestion.get_schedule_execution(saved_execution.id)
            if current_schedule is None or current_execution is None:
                raise RuntimeError("Scheduled refresh audit disappeared during execution.")
            if error_message is None and scraping_run_id is not None:
                current_execution.mark_succeeded(finished_at, scraping_run_id)
                current_schedule.mark_succeeded(finished_at)
            else:
                current_execution.mark_failed(
                    finished_at,
                    error_message or "Scheduled refresh ended without a scraping run.",
                    scraping_run_id,
                )
                current_schedule.mark_failed(finished_at)
            saved_execution = await uow.ingestion.save_schedule_execution(current_execution)
            await uow.ingestion.save_schedule(current_schedule)
            await uow.commit()
        return ScheduledRefreshExecutionDTO.from_entity(saved_execution)

    async def _load_schedule(self, schedule_id: UUID) -> ScrapingSchedule:
        async with self._unit_of_work as uow:
            schedule = await uow.ingestion.get_schedule_by_id(schedule_id)
        if schedule is None:
            raise ValueError("Scraping schedule not found.")
        return schedule

    @staticmethod
    def _format_error(error: Exception) -> str:
        return (str(error).strip() or error.__class__.__name__)[:2000]

