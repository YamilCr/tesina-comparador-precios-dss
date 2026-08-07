"""Use cases for scraping run lifecycle and audit history."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.modules.ingestion.application.commands import (
    CompleteScrapingRunCommand,
    FailScrapingRunCommand,
    StartScrapingRunCommand,
)
from app.modules.ingestion.application.dto import ScrapingRunDTO
from app.modules.ingestion.domain.entities import ScrapingRun
from app.shared.application import UnitOfWorkPort


class StartScrapingRunUseCase:
    """Starts one running audit record for an active source."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: StartScrapingRunCommand) -> ScrapingRunDTO:
        async with self._unit_of_work as uow:
            source = await uow.ingestion.get_source_by_id(command.source_id)
            if source is None:
                raise ValueError("Scraping source not found.")
            if not source.active:
                raise ValueError("Scraping source is inactive.")
            if await uow.ingestion.find_open_run(source.id) is not None:
                raise ValueError("Scraping source already has an open run.")

            run = ScrapingRun(
                id=uuid4(),
                scraping_source_id=source.id,
                started_at=datetime.now(timezone.utc),
            )
            run.mark_running()
            saved_run = await uow.ingestion.save_run(run)
            await uow.commit()
        return ScrapingRunDTO.from_entity(saved_run)


class CompleteScrapingRunUseCase:
    """Marks a running audit record as successfully completed."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: CompleteScrapingRunCommand) -> ScrapingRunDTO:
        async with self._unit_of_work as uow:
            run = await uow.ingestion.get_run_by_id(command.run_id)
            if run is None:
                raise ValueError("Scraping run not found.")
            run.mark_succeeded(
                finished_at=datetime.now(timezone.utc),
                items_scraped=command.items_scraped,
                items_loaded=command.items_loaded,
            )
            saved_run = await uow.ingestion.save_run(run)
            await uow.commit()
        return ScrapingRunDTO.from_entity(saved_run)


class FailScrapingRunUseCase:
    """Marks a running audit record as failed with a useful reason."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: FailScrapingRunCommand) -> ScrapingRunDTO:
        async with self._unit_of_work as uow:
            run = await uow.ingestion.get_run_by_id(command.run_id)
            if run is None:
                raise ValueError("Scraping run not found.")
            run.mark_failed(
                finished_at=datetime.now(timezone.utc),
                error_message=command.error_message,
            )
            saved_run = await uow.ingestion.save_run(run)
            await uow.commit()
        return ScrapingRunDTO.from_entity(saved_run)


class ListScrapingRunsUseCase:
    """Lists audit history, optionally for one configured source."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, source_id: UUID | None = None, limit: int = 100) -> list[ScrapingRunDTO]:
        async with self._unit_of_work as uow:
            if source_id is not None and await uow.ingestion.get_source_by_id(source_id) is None:
                raise ValueError("Scraping source not found.")
            runs = await uow.ingestion.list_runs(source_id=source_id, limit=limit)
        return [ScrapingRunDTO.from_entity(run) for run in runs]
