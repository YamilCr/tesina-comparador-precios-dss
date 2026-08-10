"""Integration tests for the audited extraction orchestration."""

import pytest

from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    CreateScrapingSourceUseCase,
    ExecuteScrapingRunUseCase,
    ListScrapingRunsUseCase,
    RefreshScrapingSourceUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


class SuccessfulScraper(ScraperPort):
    async def scrape(self) -> list[dict]:
        return [{"external_id": "one"}, {"external_id": "two"}]


class FailingScraper(ScraperPort):
    async def scrape(self) -> list[dict]:
        raise RuntimeError("Jumbo returned 503")


class ValidScraper(ScraperPort):
    async def scrape(self) -> list[dict]:
        return [
            {
                "external_id": "REFRESH-COCA",
                "name": "Coca Cola Original 2.25 L",
                "price": "3100.50",
                "presentation": "2.25 L",
                "url": "https://example.test/coca",
            }
        ]


@pytest.mark.asyncio
async def test_scraping_execution_audits_success_without_loading_prices(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Pilot source",
            base_url="https://example.test",
        )
    )

    result = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: SuccessfulScraper(),
    ).execute(source.id)

    assert result.run.status == "succeeded"
    assert result.run.items_scraped == 2
    assert result.run.items_loaded == 0
    assert result.items == [{"external_id": "one"}, {"external_id": "two"}]


@pytest.mark.asyncio
async def test_scraping_execution_audits_scraper_errors(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Failing pilot source",
            base_url="https://example.test",
        )
    )

    with pytest.raises(RuntimeError, match="503"):
        await ExecuteScrapingRunUseCase(
            unit_of_work,
            lambda _: FailingScraper(),
        ).execute(source.id)

    runs = await ListScrapingRunsUseCase(unit_of_work).execute(source_id=source.id)
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert runs[0].error_message == "Jumbo returned 503"


@pytest.mark.asyncio
async def test_source_refresh_executes_scraping_and_loads_price_history(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Refresh source",
            base_url="https://example.test",
            branch_id=seed_data.la_branch_id,
        )
    )

    result = await RefreshScrapingSourceUseCase(
        unit_of_work,
        lambda _: ValidScraper(),
    ).execute(source.id)

    assert result.run.status == "succeeded"
    assert result.run.items_scraped == 1
    assert result.run.items_loaded == 1
    assert result.load.loaded == 1
    assert result.load.created_prices == 1
