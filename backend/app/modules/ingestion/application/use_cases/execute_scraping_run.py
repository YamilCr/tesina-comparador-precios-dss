"""Application orchestration for one audited external extraction."""

from collections.abc import Callable
from uuid import UUID

from app.modules.ingestion.application.commands import (
    CompleteScrapingRunCommand,
    FailScrapingRunCommand,
    StartScrapingRunCommand,
)
from app.modules.ingestion.application.dto import ScrapingExecutionDTO
from app.modules.ingestion.application.use_cases.manage_scraping_runs import (
    CompleteScrapingRunUseCase,
    FailScrapingRunUseCase,
    StartScrapingRunUseCase,
)
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.application import UnitOfWorkPort


class ExecuteScrapingRunUseCase:
    """Executes extraction and records its outcome, without performing ETL loading."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        scraper_factory: Callable[[ScrapingSource], ScraperPort],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._scraper_factory = scraper_factory

    async def execute(self, source_id: UUID) -> ScrapingExecutionDTO:
        source = await self._get_source(source_id)
        started_run = await StartScrapingRunUseCase(self._unit_of_work).execute(
            StartScrapingRunCommand(source_id=source_id)
        )

        try:
            items = await self._scraper_factory(source).scrape()
        except Exception as error:
            await FailScrapingRunUseCase(self._unit_of_work).execute(
                FailScrapingRunCommand(
                    run_id=started_run.id,
                    error_message=self._format_error(error),
                )
            )
            raise

        completed_run = await CompleteScrapingRunUseCase(self._unit_of_work).execute(
            CompleteScrapingRunCommand(
                run_id=started_run.id,
                items_scraped=len(items),
                items_loaded=0,
            )
        )
        return ScrapingExecutionDTO(run=completed_run, items=items)

    async def _get_source(self, source_id: UUID) -> ScrapingSource:
        async with self._unit_of_work as uow:
            source = await uow.ingestion.get_source_by_id(source_id)
        if source is None:
            raise ValueError("Scraping source not found.")
        return source

    @staticmethod
    def _format_error(error: Exception) -> str:
        message = str(error).strip() or error.__class__.__name__
        return message[:1000]
