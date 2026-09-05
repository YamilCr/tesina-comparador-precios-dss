"""Integration coverage for reproducible sequential/concurrent benchmark metrics."""

import asyncio

import pytest

from app.experiments import collect_chain_coverage
from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    BenchmarkScrapingSourcesUseCase,
    CreateScrapingSourceUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


class SlowBenchmarkScraper(ScraperPort):
    def __init__(self, external_id: str) -> None:
        self._external_id = external_id

    async def scrape(self) -> list[dict]:
        await asyncio.sleep(0.08)
        return [
            {
                "external_id": self._external_id,
                "name": "Coca Cola Sabor Original 2.25 L",
                "price": "3200",
                "presentation": "2.25 L",
                "url": f"https://example.test/{self._external_id}",
            }
        ]


@pytest.mark.asyncio
async def test_benchmark_reports_equivalent_etl_outcomes_and_concurrent_duration(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    create_source = CreateScrapingSourceUseCase(unit_of_work)
    first = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Benchmark La Anonima",
            base_url="https://example.test/la",
            branch_id=seed_data.la_branch_id,
        )
    )
    second = await create_source.execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.carrefour_id,
            name="Benchmark Carrefour",
            base_url="https://example.test/carrefour",
            branch_id=seed_data.carrefour_branch_id,
        )
    )
    scrapers = {
        first.id: SlowBenchmarkScraper("LA-COCA-225"),
        second.id: SlowBenchmarkScraper("CAR-COCA-225"),
    }
    benchmark = BenchmarkScrapingSourcesUseCase(
        unit_of_work,
        lambda source: scrapers[source.id],
        max_concurrency=2,
        timeout_seconds=1,
    )

    sequential = await benchmark.execute([first.id, second.id], mode="sequential")
    concurrent = await benchmark.execute([first.id, second.id], mode="concurrent")

    assert [source.run.status for source in sequential.sources if source.run] == [
        "succeeded",
        "succeeded",
    ]
    assert [source.load.loaded for source in sequential.sources if source.load] == [1, 1]
    assert [source.run.status for source in concurrent.sources if source.run] == [
        "succeeded",
        "succeeded",
    ]
    assert [source.load.loaded for source in concurrent.sources if source.load] == [1, 1]
    assert all(source.duration_ms is not None for source in sequential.sources)
    assert all(source.duration_ms is not None for source in concurrent.sources)
    assert concurrent.duration_ms < sequential.duration_ms


@pytest.mark.asyncio
async def test_benchmark_requires_a_target_branch(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="No branch benchmark source",
            base_url="https://example.test/no-branch",
        )
    )
    benchmark = BenchmarkScrapingSourcesUseCase(
        unit_of_work,
        lambda _: SlowBenchmarkScraper("NO-BRANCH"),
    )

    with pytest.raises(ValueError, match="no target branch"):
        await benchmark.execute([source.id], mode="sequential")


@pytest.mark.asyncio
async def test_chain_coverage_reports_all_active_supermarkets(
    sqlite_session_factory,
) -> None:
    coverage = await collect_chain_coverage(sqlite_session_factory)

    assert {row["chain"] for row in coverage} == {"Carrefour", "La Anónima"}
    assert all(row["active_branches"] == 1 for row in coverage)
    assert all(row["verified_branches"] == 1 for row in coverage)
    assert all(row["products_with_available_price"] == 2 for row in coverage)
