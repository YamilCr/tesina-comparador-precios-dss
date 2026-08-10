"""Integration coverage for staged extraction quality and price-history loading."""

import pytest
from decimal import Decimal

from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    CreateScrapingSourceUseCase,
    ExecuteScrapingRunUseCase,
    LoadScrapingRunUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .conftest import IntegrationSeedData


class QualityScenarioScraper(ScraperPort):
    async def scrape(self) -> list[dict]:
        return [
            {
                "external_id": "LIVE-COCA",
                "name": "Gaseosa Cola Sabor Original 2.25 Lts Coca Cola",
                "price": "3100.506",
                "presentation": "2.25 L",
                "url": "https://example.test/coca",
            },
            {
                "external_id": "LIVE-COCA",
                "name": "Gaseosa Cola Sabor Original 2.25 Lts Coca Cola",
                "price": "3100.506",
            },
            {
                "external_id": "LIVE-BAD",
                "name": "Producto con precio invalido",
                "price": "-1",
            },
            {
                "external_id": "LIVE-FERNET",
                "name": "Fernet Branca 750cm3",
                "price": "18400",
                "presentation": "750 cm3",
            },
        ]


@pytest.mark.asyncio
async def test_etl_loads_valid_prices_marks_quality_issues_and_is_idempotent(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="ETL source",
            base_url="https://example.test",
            branch_id=seed_data.la_branch_id,
        )
    )
    extraction = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: QualityScenarioScraper(),
    ).execute(source.id)

    first_load = await LoadScrapingRunUseCase(unit_of_work).execute(extraction.run.id)

    assert first_load.processed == 4
    assert first_load.loaded == 2
    assert first_load.duplicates == 1
    assert first_load.rejected == 1
    assert first_load.created_products == 1
    assert first_load.created_prices == 2

    async with unit_of_work as uow:
        staged = await uow.ingestion.list_scraped_products(extraction.run.id)
        loaded_source = await uow.product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "LIVE-COCA",
        )
        run = await uow.ingestion.get_run_by_id(extraction.run.id)
        history = await uow.prices.find_history(loaded_source.id, seed_data.la_branch_id)

    assert {item.status for item in staged} == {"loaded", "duplicate", "rejected"}
    assert loaded_source is not None
    assert loaded_source.product_id == seed_data.coca_product_id
    assert run is not None and run.items_loaded == 2
    assert len(history) == 1
    assert history[0].amount == Decimal("3100.51")

    second_load = await LoadScrapingRunUseCase(unit_of_work).execute(extraction.run.id)

    assert second_load.processed == 0
    assert second_load.loaded == 0
    assert second_load.created_prices == 0


@pytest.mark.asyncio
async def test_etl_rejects_a_branch_from_a_different_supermarket(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Branch validation source",
            base_url="https://example.test",
        )
    )
    extraction = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: QualityScenarioScraper(),
    ).execute(source.id)

    with pytest.raises(ValueError, match="must belong"):
        await LoadScrapingRunUseCase(unit_of_work).execute(
            extraction.run.id,
            seed_data.carrefour_branch_id,
        )


@pytest.mark.asyncio
async def test_source_target_branch_must_belong_to_its_supermarket(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)

    with pytest.raises(ValueError, match="must belong"):
        await CreateScrapingSourceUseCase(unit_of_work).execute(
            CreateScrapingSourceCommand(
                supermarket_id=seed_data.la_anonima_id,
                name="Invalid target source",
                base_url="https://example.test",
                branch_id=seed_data.carrefour_branch_id,
            )
        )
