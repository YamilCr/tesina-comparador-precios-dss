"""Measures sequential and concurrent source refreshes using the production flow."""

from collections.abc import Callable
from time import perf_counter
from typing import Literal
from uuid import UUID

from app.modules.ingestion.application.dto import (
    ScrapingBenchmarkDTO,
    ScrapingBenchmarkSourceDTO,
    ScrapingRunDTO,
)
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.application import UnitOfWorkPort

from .concurrent_refresh_scraping_sources import ConcurrentRefreshScrapingSourcesUseCase
from .refresh_scraping_source import RefreshScrapingSourceUseCase


BenchmarkMode = Literal["sequential", "concurrent"]


class BenchmarkScrapingSourcesUseCase:
    """Runs one repeatable end-to-end benchmark iteration without changing source code paths."""

    def __init__(
        self,
        unit_of_work: UnitOfWorkPort,
        scraper_factory: Callable[[ScrapingSource], ScraperPort],
        *,
        max_concurrency: int = 3,
        timeout_seconds: int = 20,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._scraper_factory = scraper_factory
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds

    async def execute(
        self,
        source_ids: list[UUID],
        *,
        mode: BenchmarkMode,
    ) -> ScrapingBenchmarkDTO:
        sources = await self._validate_sources(source_ids)
        began_at = perf_counter()
        if mode == "sequential":
            results = await self._run_sequential(sources)
        else:
            results = await self._run_concurrent(sources)
        return ScrapingBenchmarkDTO(
            mode=mode,
            duration_ms=_elapsed_ms(began_at),
            sources=results,
        )

    async def _validate_sources(self, source_ids: list[UUID]) -> list[ScrapingSource]:
        unique_source_ids = list(dict.fromkeys(source_ids))
        if not unique_source_ids:
            raise ValueError("At least one scraping source is required.")

        async with self._unit_of_work as uow:
            sources = []
            for source_id in unique_source_ids:
                source = await uow.ingestion.get_source_by_id(source_id)
                if source is None:
                    raise ValueError(f"Scraping source {source_id} was not found.")
                if not source.active:
                    raise ValueError(f"Scraping source {source.name!r} is inactive.")
                if source.branch_id is None:
                    raise ValueError(
                        f"Scraping source {source.name!r} has no target branch for ETL loading."
                    )
                sources.append(source)
        return sources

    async def _run_sequential(
        self,
        sources: list[ScrapingSource],
    ) -> list[ScrapingBenchmarkSourceDTO]:
        results = []
        refresh = RefreshScrapingSourceUseCase(self._unit_of_work, self._scraper_factory)
        for source in sources:
            try:
                result = await refresh.execute(source.id)
            except Exception as error:
                results.append(
                    ScrapingBenchmarkSourceDTO(
                        source_id=source.id,
                        source_name=source.name,
                        run=await self._latest_run(source.id),
                        error_message=_format_error(error),
                    )
                )
                continue
            results.append(
                ScrapingBenchmarkSourceDTO(
                    source_id=source.id,
                    source_name=source.name,
                    run=result.run,
                    load=result.load,
                )
            )
        return results

    async def _run_concurrent(
        self,
        sources: list[ScrapingSource],
    ) -> list[ScrapingBenchmarkSourceDTO]:
        result = await ConcurrentRefreshScrapingSourcesUseCase(
            self._unit_of_work,
            self._scraper_factory,
            max_concurrency=self._max_concurrency,
            timeout_seconds=self._timeout_seconds,
        ).execute([source.id for source in sources])
        return [
            ScrapingBenchmarkSourceDTO(
                source_id=source.source_id,
                source_name=source.source_name,
                run=source.run,
                load=source.load,
                error_message=source.error_message,
            )
            for source in result.results
        ]

    async def _latest_run(self, source_id: UUID) -> ScrapingRunDTO | None:
        async with self._unit_of_work as uow:
            runs = await uow.ingestion.list_runs(source_id=source_id, limit=1)
        return ScrapingRunDTO.from_entity(runs[0]) if runs else None


def _elapsed_ms(began_at: float) -> int:
    return round((perf_counter() - began_at) * 1000)


def _format_error(error: Exception) -> str:
    return (str(error).strip() or error.__class__.__name__)[:1000]
