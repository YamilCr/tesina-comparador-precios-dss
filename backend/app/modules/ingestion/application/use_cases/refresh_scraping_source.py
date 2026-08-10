"""Orchestrates one complete source refresh from extraction through ETL loading."""

from collections.abc import Callable
from uuid import UUID

from app.modules.ingestion.application.dto import ScrapingRefreshDTO, ScrapingRunDTO
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.application import UnitOfWorkPort

from .execute_scraping_run import ExecuteScrapingRunUseCase
from .load_scraping_run import LoadScrapingRunUseCase


class RefreshScrapingSourceUseCase:
    """Runs an audited extraction and loads its validated results in one operation."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        scraper_factory: Callable[[ScrapingSource], ScraperPort],
    ) -> None:
        self._unit_of_work = unit_of_work
        self._scraper_factory = scraper_factory

    async def execute(self, source_id: UUID) -> ScrapingRefreshDTO:
        extraction = await ExecuteScrapingRunUseCase(
            self._unit_of_work,
            self._scraper_factory,
        ).execute(source_id)
        load = await LoadScrapingRunUseCase(self._unit_of_work).execute(extraction.run.id)
        async with self._unit_of_work as uow:
            run = await uow.ingestion.get_run_by_id(extraction.run.id)
        if run is None:
            raise RuntimeError("Scraping run disappeared after loading.")
        return ScrapingRefreshDTO(run=ScrapingRunDTO.from_entity(run), load=load)
