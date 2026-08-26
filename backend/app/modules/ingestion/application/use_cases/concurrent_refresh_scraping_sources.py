"""Coordinates concurrent network extraction with serialized ETL persistence."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from uuid import UUID

from app.modules.ingestion.application.commands import (
    CompleteScrapingRunCommand,
    FailScrapingRunCommand,
    StartScrapingRunCommand,
)
from app.modules.ingestion.application.dto import (
    ConcurrentScrapingRefreshDTO,
    ConcurrentScrapingSourceResultDTO,
    ScrapingRunDTO,
)
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.application import UnitOfWorkPort

from .load_scraping_run import LoadScrapingRunUseCase
from .manage_scraping_runs import (
    CompleteScrapingRunUseCase,
    FailScrapingRunUseCase,
    StartScrapingRunUseCase,
)
from .store_scraped_products import StoreScrapedProductsUseCase


@dataclass(frozen=True)
class _StartedSourceRun:
    source: ScrapingSource
    run: ScrapingRunDTO


@dataclass(frozen=True)
class _ExtractionOutcome:
    started: _StartedSourceRun
    items: list[dict] | None
    duration_ms: int
    error_message: str | None = None


class ConcurrentRefreshScrapingSourcesUseCase:
    """Runs source I/O concurrently, then persists each audited result serially."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        scraper_factory: Callable[[ScrapingSource], ScraperPort],
        *,
        max_concurrency: int = 3,
        timeout_seconds: int = 20,
    ) -> None:
        if max_concurrency < 1:
            raise ValueError("Max concurrency must be at least one.")
        if timeout_seconds < 1:
            raise ValueError("Source timeout must be at least one second.")
        self._unit_of_work = unit_of_work
        self._scraper_factory = scraper_factory
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds

    async def execute(self, source_ids: list[UUID]) -> ConcurrentScrapingRefreshDTO:
        unique_source_ids = list(dict.fromkeys(source_ids))
        if not unique_source_ids:
            raise ValueError("At least one scraping source is required.")

        started_runs = await self._start_runs(unique_source_ids)
        queue: asyncio.Queue[_ExtractionOutcome] = asyncio.Queue()
        semaphore = asyncio.Semaphore(self._max_concurrency)
        results: list[ConcurrentScrapingSourceResultDTO] = []

        async with asyncio.TaskGroup() as task_group:
            for started in started_runs:
                task_group.create_task(self._extract_to_queue(started, semaphore, queue))
            for _ in range(len(started_runs)):
                results.append(await self._persist_outcome(await queue.get()))
        return ConcurrentScrapingRefreshDTO(results=results)

    async def _start_runs(self, source_ids: list[UUID]) -> list[_StartedSourceRun]:
        async with self._unit_of_work as uow:
            sources = []
            for source_id in source_ids:
                source = await uow.ingestion.get_source_by_id(source_id)
                if source is None:
                    raise ValueError("Scraping source not found.")
                if not source.active:
                    raise ValueError("Scraping source is inactive.")
                sources.append(source)

        started_runs = []
        for source in sources:
            run = await StartScrapingRunUseCase(self._unit_of_work).execute(
                StartScrapingRunCommand(source_id=source.id)
            )
            started_runs.append(_StartedSourceRun(source=source, run=run))
        return started_runs

    async def _extract_to_queue(
        self,
        started: _StartedSourceRun,
        semaphore: asyncio.Semaphore,
        queue: asyncio.Queue[_ExtractionOutcome],
    ) -> None:
        began_at = perf_counter()
        try:
            async with semaphore, asyncio.timeout(self._timeout_seconds):
                items = await self._scraper_factory(started.source).scrape()
        except Exception as error:
            await queue.put(
                _ExtractionOutcome(
                    started=started,
                    items=None,
                    duration_ms=_elapsed_ms(began_at),
                    error_message=_format_error(error),
                )
            )
            return
        await queue.put(
            _ExtractionOutcome(
                started=started,
                items=items,
                duration_ms=_elapsed_ms(began_at),
            )
        )

    async def _persist_outcome(
        self,
        outcome: _ExtractionOutcome,
    ) -> ConcurrentScrapingSourceResultDTO:
        if outcome.error_message is not None:
            run = await self._fail_run(outcome.started.run.id, outcome.error_message)
            return self._result(outcome, run=run, error_message=outcome.error_message)

        try:
            await StoreScrapedProductsUseCase(self._unit_of_work).execute(
                outcome.started.run.id,
                outcome.items or [],
            )
        except Exception as error:
            error_message = _format_error(error)
            run = await self._fail_run(outcome.started.run.id, error_message)
            return self._result(outcome, run=run, error_message=error_message)

        try:
            await CompleteScrapingRunUseCase(self._unit_of_work).execute(
                CompleteScrapingRunCommand(
                    run_id=outcome.started.run.id,
                    items_scraped=len(outcome.items or []),
                    items_loaded=0,
                )
            )
            load = await LoadScrapingRunUseCase(self._unit_of_work).execute(outcome.started.run.id)
            async with self._unit_of_work as uow:
                completed_run = await uow.ingestion.get_run_by_id(outcome.started.run.id)
            if completed_run is None:
                raise RuntimeError("Scraping run disappeared after loading.")
            return self._result(
                outcome,
                run=ScrapingRunDTO.from_entity(completed_run),
                load=load,
            )
        except Exception as error:
            async with self._unit_of_work as uow:
                current_run = await uow.ingestion.get_run_by_id(outcome.started.run.id)
            return self._result(
                outcome,
                run=(
                    ScrapingRunDTO.from_entity(current_run)
                    if current_run is not None
                    else outcome.started.run
                ),
                error_message=_format_error(error),
            )

    async def _fail_run(self, run_id: UUID, error_message: str) -> ScrapingRunDTO:
        return await FailScrapingRunUseCase(self._unit_of_work).execute(
            FailScrapingRunCommand(run_id=run_id, error_message=error_message)
        )

    @staticmethod
    def _result(
        outcome: _ExtractionOutcome,
        *,
        run: ScrapingRunDTO,
        load=None,
        error_message: str | None = None,
    ) -> ConcurrentScrapingSourceResultDTO:
        return ConcurrentScrapingSourceResultDTO(
            source_id=outcome.started.source.id,
            source_name=outcome.started.source.name,
            run=run,
            duration_ms=outcome.duration_ms,
            load=load,
            error_message=error_message,
        )


def _elapsed_ms(began_at: float) -> int:
    return round((perf_counter() - began_at) * 1000)


def _format_error(error: Exception) -> str:
    return (str(error).strip() or error.__class__.__name__)[:1000]
