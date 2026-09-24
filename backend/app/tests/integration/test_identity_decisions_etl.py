from uuid import uuid4

import pytest

from app.modules.catalog.domain.entities import Product
from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    CreateScrapingSourceUseCase, ExecuteScrapingRunUseCase, LoadScrapingRunUseCase,
)
from app.shared.infrastructure import SQLAlchemyUnitOfWork

from .test_etl_loading import StaticScraper


@pytest.mark.asyncio
async def test_ambiguous_identity_stays_in_staging_without_new_product(sqlite_session_factory, seed_data):
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)
    async with uow as tx:
        for _ in range(2):
            await tx.products.save(Product(uuid4(), "Arroz Prueba 500 g"))
        await tx.commit()
    source = await CreateScrapingSourceUseCase(uow).execute(CreateScrapingSourceCommand(
        supermarket_id=seed_data.la_anonima_id, branch_id=seed_data.la_branch_id,
        name="Ambiguity regression", base_url="https://example.test",
    ))
    extraction = await ExecuteScrapingRunUseCase(uow, lambda _: StaticScraper([{
        "external_id": "AMBIGUOUS", "name": "Arroz Prueba 500 g", "price": "1000",
    }])).execute(source.id)
    result = await LoadScrapingRunUseCase(uow).execute(extraction.run.id)
    assert result.unmatched == 1
    assert result.created_products == result.created_prices == result.loaded == 0
    repeated = await LoadScrapingRunUseCase(uow).execute(extraction.run.id)
    assert repeated.unmatched == 1
    assert repeated.created_products == 0


@pytest.mark.asyncio
async def test_new_product_keeps_explicit_brand_and_category(sqlite_session_factory, seed_data):
    uow = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(uow).execute(CreateScrapingSourceCommand(
        supermarket_id=seed_data.la_anonima_id, branch_id=seed_data.la_branch_id,
        name="Attribute regression", base_url="https://example.test",
    ))
    extraction = await ExecuteScrapingRunUseCase(uow, lambda _: StaticScraper([{
        "external_id": "ATTRIBUTES", "name": "Arroz Prueba 500 g", "price": "1000",
        "brand": "Prueba", "categories": ["/Almacen/Arroz/", "/Almacen/"],
    }])).execute(source.id)
    result = await LoadScrapingRunUseCase(uow).execute(extraction.run.id)
    assert result.created_products == 1
    async with uow as tx:
        publication = await tx.product_sources.find_by_external_code(seed_data.la_anonima_id, "ATTRIBUTES")
        product = await tx.products.get_by_id(publication.product_id)
        assert (await tx.brands.get_by_id(product.brand_id)).name == "Prueba"
        assert (await tx.product_categories.get_by_id(product.category_id)).name == "Arroz"
