"""Integration coverage for staged extraction quality and price-history loading."""

import pytest
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.modules.ingestion.application.commands import CreateScrapingSourceCommand
from app.modules.ingestion.application.use_cases import (
    ConsolidateProductCatalogUseCase,
    CreateScrapingSourceUseCase,
    DecideProductIdentityReviewUseCase,
    EnrichProductCatalogUseCase,
    ExecuteScrapingRunUseCase,
    LoadScrapingRunUseCase,
    GenerateProductIdentityReviewsUseCase,
    ReconcileProductIdentityUseCase,
)
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.catalog.infrastructure.persistence import ProductModel, ProductSourceModel
from app.modules.prices.infrastructure.persistence import PriceModel
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


class StaticScraper(ScraperPort):
    def __init__(self, products: list[dict]) -> None:
        self._products = products

    async def scrape(self) -> list[dict]:
        return self._products


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


@pytest.mark.asyncio
async def test_etl_reuses_canonical_product_for_equivalent_packaging(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Equivalent packaging source",
            base_url="https://example.test",
            branch_id=seed_data.la_branch_id,
        )
    )
    products = [
        {
            "external_id": "COOPE-COCA-2250",
            "ean": "internal-2250",
            "name": "Gaseosa Coca-Cola sabor original descartable 2250cm3",
            "brand": "Coca Cola",
            "presentation": "2250 cm3",
            "price": "3299.90",
        }
    ]
    extraction = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: StaticScraper(products),
    ).execute(source.id)

    result = await LoadScrapingRunUseCase(unit_of_work).execute(extraction.run.id)

    async with unit_of_work as uow:
        loaded_source = await uow.product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "COOPE-COCA-2250",
        )

    assert result.created_products == 0
    assert result.loaded == 1
    assert loaded_source is not None
    assert loaded_source.product_id == seed_data.coca_product_id
    assert loaded_source.gtin is None


@pytest.mark.asyncio
async def test_etl_prioritizes_global_gtin_over_different_source_text(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    valid_gtin = "4006381333931"
    async with sqlite_session_factory() as session:
        known_source = await session.get(ProductSourceModel, seed_data.la_coca_source_id)
        assert known_source is not None
        known_source.gtin = valid_gtin
        await session.commit()

    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.carrefour_id,
            name="GTIN source",
            base_url="https://example.test",
            branch_id=seed_data.carrefour_branch_id,
        )
    )
    products = [
        {
            "external_id": "CAR-GTIN-NEW",
            "ean": valid_gtin,
            "identifier_type": "gtin",
            "name": "Texto comercial completamente diferente 900 ml",
            "brand": "Marca externa",
            "price": "4100",
        }
    ]
    extraction = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: StaticScraper(products),
    ).execute(source.id)

    result = await LoadScrapingRunUseCase(unit_of_work).execute(extraction.run.id)

    async with unit_of_work as uow:
        loaded_source = await uow.product_sources.find_by_external_code(
            seed_data.carrefour_id,
            "CAR-GTIN-NEW",
        )

    assert result.created_products == 0
    assert loaded_source is not None
    assert loaded_source.product_id == seed_data.coca_product_id
    assert loaded_source.gtin == valid_gtin


@pytest.mark.asyncio
async def test_reconciliation_reassigns_source_and_preserves_price_history(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    weak_product_id = uuid4()
    weak_source_id = uuid4()
    weak_price_id = uuid4()
    async with sqlite_session_factory() as session:
        session.add_all(
            [
                ProductModel(
                    id=weak_product_id,
                    nombre_normalizado=(
                        "Gaseosa Coca-Cola sabor original descartable 2250cm3"
                    ),
                    activo=True,
                ),
                ProductSourceModel(
                    id=weak_source_id,
                    producto_id=weak_product_id,
                    supermercado_id=seed_data.carrefour_id,
                    nombre_original=(
                        "Gaseosa Coca-Cola sabor original descartable 2250cm3"
                    ),
                    codigo_externo="HISTORICAL-COCA-2250",
                    unidad_original="2250 cm3",
                    confianza_match=Decimal("1.000"),
                    activo=True,
                ),
                PriceModel(
                    id=weak_price_id,
                    producto_fuente_id=weak_source_id,
                    sucursal_id=seed_data.carrefour_branch_id,
                    precio=Decimal("3300.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed_data.observed_at,
                    disponible=True,
                    promocion=False,
                ),
            ]
        )
        await session.commit()

    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    use_case = ReconcileProductIdentityUseCase(unit_of_work)

    dry_run = await use_case.execute()

    assert dry_run.dry_run is True
    assert len(dry_run.suggestions) == 1
    assert dry_run.suggestions[0].target_product_id == seed_data.coca_product_id

    applied = await use_case.execute(apply=True)

    async with unit_of_work as uow:
        product_source = await uow.product_sources.find_by_external_code(
            seed_data.carrefour_id,
            "HISTORICAL-COCA-2250",
        )
        weak_product = await uow.products.get_by_id(weak_product_id)
        price_history = await uow.prices.find_history(
            weak_source_id,
            seed_data.carrefour_branch_id,
        )

    assert applied.reassigned_sources == 1
    assert product_source is not None
    assert product_source.product_id == seed_data.coca_product_id
    assert weak_product is not None and weak_product.active is False
    assert [price.id for price in price_history] == [weak_price_id]


@pytest.mark.asyncio
async def test_catalog_consolidation_merges_exact_multichain_products_and_keeps_prices(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    first_product_id = uuid4()
    second_product_id = uuid4()
    first_source_id = uuid4()
    second_source_id = uuid4()
    first_price_id = uuid4()
    second_price_id = uuid4()
    async with sqlite_session_factory() as session:
        session.add_all(
            [
                ProductModel(
                    id=first_product_id,
                    nombre_normalizado="Fernet Branca x 750 cc.",
                    activo=True,
                ),
                ProductModel(
                    id=second_product_id,
                    nombre_normalizado="fernet branca 750cm3",
                    activo=True,
                ),
                ProductSourceModel(
                    id=first_source_id,
                    producto_id=first_product_id,
                    supermercado_id=seed_data.la_anonima_id,
                    nombre_original="Fernet Branca x 750 cc.",
                    codigo_externo="LA-FERNET-BRANCA-750",
                    confianza_match=Decimal("1.000"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=second_source_id,
                    producto_id=second_product_id,
                    supermercado_id=seed_data.carrefour_id,
                    nombre_original="fernet branca 750cm3",
                    codigo_externo="CAR-FERNET-BRANCA-750",
                    confianza_match=Decimal("1.000"),
                    activo=True,
                ),
                PriceModel(
                    id=first_price_id,
                    producto_fuente_id=first_source_id,
                    sucursal_id=seed_data.la_branch_id,
                    precio=Decimal("12000.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed_data.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=second_price_id,
                    producto_fuente_id=second_source_id,
                    sucursal_id=seed_data.carrefour_branch_id,
                    precio=Decimal("11800.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed_data.observed_at,
                    disponible=True,
                    promocion=False,
                ),
            ]
        )
        await session.commit()

    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    use_case = ConsolidateProductCatalogUseCase(unit_of_work)

    dry_run = await use_case.execute()

    assert dry_run.dry_run is True
    assert len(dry_run.clusters) == 1
    target_id = dry_run.clusters[0].target_product_id
    duplicate_id = next(
        product_id
        for product_id in (first_product_id, second_product_id)
        if product_id != target_id
    )

    applied = await use_case.execute(apply=True)

    async with unit_of_work as uow:
        first_source = await uow.product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "LA-FERNET-BRANCA-750",
        )
        second_source = await uow.product_sources.find_by_external_code(
            seed_data.carrefour_id,
            "CAR-FERNET-BRANCA-750",
        )
        target = await uow.products.get_by_id(target_id)
        duplicate = await uow.products.get_by_id(duplicate_id)
        first_history = await uow.prices.find_history(
            first_source_id,
            seed_data.la_branch_id,
        )
        second_history = await uow.prices.find_history(
            second_source_id,
            seed_data.carrefour_branch_id,
        )

    assert applied.reassigned_sources == 1
    assert applied.deactivated_products == 1
    assert applied.enriched_products == 1
    assert first_source is not None and first_source.product_id == target_id
    assert second_source is not None and second_source.product_id == target_id
    assert target is not None
    assert target.unit_measure == "L"
    assert target.net_content == Decimal("0.750")
    assert duplicate is not None and duplicate.active is False
    assert [price.id for price in first_history] == [first_price_id]
    assert [price.id for price in second_history] == [second_price_id]

    repeated = await use_case.execute()
    assert repeated.clusters == []


@pytest.mark.asyncio
async def test_catalog_enrichment_backfills_consensus_brand_and_declared_gtin(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    valid_gtin = "4006381333931"
    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    scraping_source = await CreateScrapingSourceUseCase(unit_of_work).execute(
        CreateScrapingSourceCommand(
            supermarket_id=seed_data.la_anonima_id,
            name="Historical enrichment source",
            base_url="https://example.test",
            branch_id=seed_data.la_branch_id,
        )
    )
    products = [
        {
            "external_id": "HISTORICAL-SMIRNOFF-700",
            "ean": valid_gtin,
            "identifier_type": "gtin",
            "name": "Vodka Smirnoff 700 ml",
            "brand": "Smirnoff",
            "presentation": "700 ml",
            "price": "10500",
        }
    ]
    extraction = await ExecuteScrapingRunUseCase(
        unit_of_work,
        lambda _: StaticScraper(products),
    ).execute(scraping_source.id)
    await LoadScrapingRunUseCase(unit_of_work).execute(extraction.run.id)

    async with sqlite_session_factory() as session:
        publication = await session.scalar(
            select(ProductSourceModel).where(
                ProductSourceModel.codigo_externo == "HISTORICAL-SMIRNOFF-700"
            )
        )
        assert publication is not None
        product_id = publication.producto_id
        publication.gtin = None
        await session.commit()

    use_case = EnrichProductCatalogUseCase(unit_of_work)
    dry_run = await use_case.execute()

    assert len(dry_run.brand_suggestions) == 1
    assert dry_run.brand_suggestions[0].brand_name == "Smirnoff"
    assert dry_run.brand_suggestions[0].creates_brand is True
    assert len(dry_run.gtin_suggestions) == 1
    assert dry_run.gtin_suggestions[0].gtin == valid_gtin
    assert dry_run.gtin_conflicts == []

    applied = await use_case.execute(apply=True)

    async with unit_of_work as uow:
        publication = await uow.product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "HISTORICAL-SMIRNOFF-700",
        )
        product = await uow.products.get_by_id(product_id)
        assert product is not None
        brand = await uow.brands.get_by_id(product.brand_id)

    assert applied.created_brands == 1
    assert applied.enriched_products == 1
    assert applied.enriched_product_sources == 1
    assert publication is not None and publication.gtin == valid_gtin
    assert brand is not None and brand.name == "Smirnoff"

    repeated = await use_case.execute()
    assert repeated.brand_suggestions == []
    assert repeated.gtin_suggestions == []


@pytest.mark.asyncio
async def test_assisted_semantic_review_approval_merges_products_and_keeps_prices(
    sqlite_session_factory,
    seed_data: IntegrationSeedData,
) -> None:
    zero_product_id = uuid4()
    sugar_free_product_id = uuid4()
    zero_source_id = uuid4()
    sugar_free_source_id = uuid4()
    zero_price_id = uuid4()
    sugar_free_price_id = uuid4()
    async with sqlite_session_factory() as session:
        session.add_all(
            [
                ProductModel(
                    id=zero_product_id,
                    marca_id=seed_data.brand_coca_id,
                    nombre_normalizado="Coca Cola Zero 1.75 L",
                    unidad_medida="L",
                    contenido_neto=Decimal("1.750"),
                    activo=True,
                ),
                ProductModel(
                    id=sugar_free_product_id,
                    marca_id=seed_data.brand_coca_id,
                    nombre_normalizado="Coca Cola Sin Azúcar 1,75 L",
                    unidad_medida="L",
                    contenido_neto=Decimal("1.750"),
                    activo=True,
                ),
                ProductSourceModel(
                    id=zero_source_id,
                    producto_id=zero_product_id,
                    supermercado_id=seed_data.la_anonima_id,
                    nombre_original="Coca Cola Zero 1.75 L",
                    codigo_externo="LA-COCA-ZERO-175",
                    activo=True,
                ),
                ProductSourceModel(
                    id=sugar_free_source_id,
                    producto_id=sugar_free_product_id,
                    supermercado_id=seed_data.carrefour_id,
                    nombre_original="Coca Cola Sin Azúcar 1,75 L",
                    codigo_externo="CAR-COCA-SUGARFREE-175",
                    activo=True,
                ),
                PriceModel(
                    id=zero_price_id,
                    producto_fuente_id=zero_source_id,
                    sucursal_id=seed_data.la_branch_id,
                    precio=Decimal("3000.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed_data.observed_at,
                    disponible=True,
                    promocion=False,
                ),
                PriceModel(
                    id=sugar_free_price_id,
                    producto_fuente_id=sugar_free_source_id,
                    sucursal_id=seed_data.carrefour_branch_id,
                    precio=Decimal("3100.00"),
                    moneda="ARS",
                    fecha_relevamiento=seed_data.observed_at,
                    disponible=True,
                    promocion=False,
                ),
            ]
        )
        await session.commit()

    unit_of_work = SQLAlchemyUnitOfWork(sqlite_session_factory)
    generated = await GenerateProductIdentityReviewsUseCase(unit_of_work).execute()

    assert generated.generated == 1
    assert generated.semantic_candidates == 1
    async with unit_of_work as uow:
        reviews = await uow.ingestion.list_identity_reviews(status="pending")
    assert len(reviews) == 1
    assert reviews[0].review_type == "semantic_alias"

    repeated = await GenerateProductIdentityReviewsUseCase(unit_of_work).execute()
    assert repeated.generated == 0

    decision = await DecideProductIdentityReviewUseCase(unit_of_work).execute(
        reviews[0].id,
        decision="approve",
        note="Same Coca Cola variant and 1.75 L package confirmed.",
    )

    async with unit_of_work as uow:
        approved = await uow.ingestion.get_identity_review(reviews[0].id)
        source_product = await uow.products.get_by_id(reviews[0].source_product_id)
        zero_source = await uow.product_sources.find_by_external_code(
            seed_data.la_anonima_id,
            "LA-COCA-ZERO-175",
        )
        sugar_free_source = await uow.product_sources.find_by_external_code(
            seed_data.carrefour_id,
            "CAR-COCA-SUGARFREE-175",
        )
        zero_history = await uow.prices.find_history(zero_source_id, seed_data.la_branch_id)
        sugar_free_history = await uow.prices.find_history(
            sugar_free_source_id,
            seed_data.carrefour_branch_id,
        )

    assert decision.reassigned_sources == 1
    assert approved is not None and approved.status == "approved"
    assert source_product is not None and source_product.active is False
    assert zero_source is not None and sugar_free_source is not None
    assert zero_source.product_id == sugar_free_source.product_id
    assert [price.id for price in zero_history] == [zero_price_id]
    assert [price.id for price in sugar_free_history] == [sugar_free_price_id]
