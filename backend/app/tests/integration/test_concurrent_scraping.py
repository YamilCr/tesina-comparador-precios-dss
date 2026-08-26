"""Integration coverage for bounded concurrent extraction and serialized ETL loading."""

import asyncio
from dataclasses import dataclass

import pytest

from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    ConcurrentRefreshScrapingSourcesUseCase,
    CreateScrapingSourceUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


@dataclass
class ConcurrencyTracker:
    active: int = 0
    maximum: int = 0


class DelayedScraper(ScraperPort):
    def __init__(
        self,
        tracker: ConcurrencyTracker,
        *,
        external_id: str,
        delay: float = 0.04,
        fails: bool = False,
    ) -> None:
        self._tracker = tracker
        self._external_id = external_id
        self._delay = delay
        self._fails = fails

    async def scrape(self) -> list[dict]:
        self._tracker.active += 1
        self._tracker.maximum = max(self._tracker.maximum, self._tracker.active)
        try:
            await asyncio.sleep(self._delay)
            if self._fails:
                raise RuntimeError("Remote source unavailable")
            return [
                {
                    "external_id": self._external_id,
                    "name": "Coca Cola Sabor Original 2.25 L",
                    "price": "3200",
                    "presentation": "2.25 L",
                    "url": f"https://example.test/{self._external_id}",
                }
            ]
        finally:
            self._tracker.active -= 1


@pytest.mark.asyncio
async def test_concurrent_refresh_bounds_network_work_and_preserves_partial_results(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    create_source = CreateScrapingSourceUseCase(unit_of_work)
    first = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Concurrent La Anonima",
            base_url="https://example.test/la",
            branch_id=seed_data.la_branch_id,
        )
    )
    second = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.carrefour_id,
            name="Concurrent Carrefour",
            base_url="https://example.test/carrefour",
            branch_id=seed_data.carrefour_branch_id,
        )
    )
    third = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Concurrent failure",
            base_url="https://example.test/failure",
            branch_id=seed_data.la_branch_id,
        )
    )
    tracker = ConcurrencyTracker()
    scrapers = {
        first.id: DelayedScraper(tracker, external_id="LA-COCA-225"),
        second.id: DelayedScraper(tracker, external_id="CAR-COCA-225"),
        third.id: DelayedScraper(tracker, external_id="FAIL-COCA", fails=True),
    }

    refresh = await ConcurrentRefreshScrapingSourcesUseCase(
        unit_of_work,
        lambda source: scrapers[source.id],
        max_concurrency=2,
        timeout_seconds=1,
    ).execute([first.id, second.id, third.id])

    assert tracker.maximum == 2
    results = {result.source_id: result for result in refresh.results}
    assert results[first.id].run.status == "succeeded"
    assert results[first.id].load is not None
    assert results[second.id].run.status == "succeeded"
    assert results[second.id].load is not None
    assert results[third.id].run.status == "failed"
    assert results[third.id].load is None
    assert results[third.id].error_message == "Remote source unavailable"
