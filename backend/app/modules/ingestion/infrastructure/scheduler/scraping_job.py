"""Lightweight async scheduler for persistent ingestion refresh plans."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone

from app.modules.ingestion.application.dto import (
    ScheduledRefreshExecutionDTO,
    ScrapingScheduleDTO,
)
from app.modules.ingestion.application.use_cases import (
    ClaimDueScrapingSchedulesUseCase,
    RunScrapingScheduleUseCase,
)
from app.modules.ingestion.domain.entities import ScrapingSchedule, ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.ingestion.infrastructure.scrapers import create_scraper_for_source
from app.shared.application import UnitOfWorkPort


logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWorkPort]


def _create_scheduled_scraper(
    source: ScrapingSource,
    schedule: ScrapingSchedule,
) -> ScraperPort:
    return create_scraper_for_source(
        source,
        queries=list(schedule.queries),
        city=schedule.city,
        result_limit=schedule.result_limit,
    )


class ScrapingScheduler:
    """Polls persistent plans and executes claimed jobs with bounded concurrency."""

    def __init__(
        self,
        unit_of_work_factory: UnitOfWorkFactory,
        *,
        poll_seconds: int = 30,
        batch_size: int = 10,
        max_concurrency: int = 3,
        lease_seconds: int = 900,
        scraper_factory: Callable[
            [ScrapingSource, ScrapingSchedule], ScraperPort
        ] = _create_scheduled_scraper,
    ) -> None:
        if poll_seconds < 1 or batch_size < 1 or max_concurrency < 1:
            raise ValueError("Scheduler polling and concurrency values must be positive.")
        if lease_seconds < 60:
            raise ValueError("Scheduler lease must be at least 60 seconds.")
        self._unit_of_work_factory = unit_of_work_factory
        self._poll_seconds = poll_seconds
        self._batch_size = batch_size
        self._max_concurrency = max_concurrency
        self._lease_seconds = lease_seconds
        self._scraper_factory = scraper_factory
        self._stop_event = asyncio.Event()
        self._poll_lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Starts one background polling task for this application process."""
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="ingestion-scheduler")
        logger.info("Ingestion scheduler started")

    async def stop(self) -> None:
        """Stops polling and waits for in-flight refreshes to finish cleanly."""
        if self._task is None:
            return
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Ingestion scheduler stopped")

    async def run_due_once(self) -> list[ScheduledRefreshExecutionDTO]:
        """Claims and processes one due batch; exposed separately for deterministic tests."""
        async with self._poll_lock:
            now = datetime.now(timezone.utc)
            claimed = await ClaimDueScrapingSchedulesUseCase(
                self._unit_of_work_factory()
            ).execute(
                now=now,
                lease_seconds=self._lease_seconds,
                limit=self._batch_size,
            )
            if not claimed:
                return []

            semaphore = asyncio.Semaphore(self._max_concurrency)
            tasks: list[asyncio.Task[ScheduledRefreshExecutionDTO | None]] = []
            async with asyncio.TaskGroup() as task_group:
                for schedule in claimed:
                    tasks.append(
                        task_group.create_task(
                            self._run_claimed_schedule(schedule, semaphore)
                        )
                    )
            return [result for task in tasks if (result := task.result()) is not None]

    async def _run_claimed_schedule(
        self,
        schedule: ScrapingScheduleDTO,
        semaphore: asyncio.Semaphore,
    ) -> ScheduledRefreshExecutionDTO | None:
        try:
            async with semaphore:
                return await RunScrapingScheduleUseCase(
                    self._unit_of_work_factory(),
                    self._scraper_factory,
                ).execute(
                    schedule.id,
                    scheduled_for=schedule.next_run_at,
                )
        except Exception:
            logger.exception("Unexpected scheduler failure for schedule %s", schedule.id)
            return None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.run_due_once()
            except Exception:
                logger.exception("Unexpected ingestion scheduler polling failure")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self._poll_seconds,
                )
            except TimeoutError:
                continue
