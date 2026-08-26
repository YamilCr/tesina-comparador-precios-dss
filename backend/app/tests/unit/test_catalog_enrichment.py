"""Unit coverage for evidence conflicts during catalog enrichment."""

from uuid import uuid4

from app.modules.catalog.domain.entities import ProductSource
from app.modules.ingestion.application.use_cases.enrich_product_catalog import (
    _gtin_suggestions,
)
from app.modules.ingestion.domain.entities import ScrapedProduct


def test_gtin_linked_to_two_products_is_reported_and_not_backfilled() -> None:
    gtin = "4006381333931"
    supermarket_id = uuid4()
    first_source = ProductSource(
        id=uuid4(),
        product_id=uuid4(),
        supermarket_id=supermarket_id,
        original_name="First product",
    )
    second_source = ProductSource(
        id=uuid4(),
        product_id=uuid4(),
        supermarket_id=supermarket_id,
        original_name="Second product",
    )
    evidence = [
        ScrapedProduct(
            id=uuid4(),
            scraping_run_id=uuid4(),
            raw_payload={"identifier_type": "gtin"},
            ean=gtin,
            status="loaded",
            product_source_id=source.id,
        )
        for source in (first_source, second_source)
    ]

    suggestions, conflicts = _gtin_suggestions(
        evidence=evidence,
        sources_by_id={
            first_source.id: first_source,
            second_source.id: second_source,
        },
    )

    assert suggestions == []
    assert len(conflicts) == 1
    assert conflicts[0].gtin == gtin
    assert set(conflicts[0].product_ids) == {
        first_source.product_id,
        second_source.product_id,
    }


def test_internal_identifier_is_never_used_as_gtin_even_with_valid_checksum() -> None:
    source = ProductSource(
        id=uuid4(),
        product_id=uuid4(),
        supermarket_id=uuid4(),
        original_name="Internal product",
    )
    evidence = [
        ScrapedProduct(
            id=uuid4(),
            scraping_run_id=uuid4(),
            raw_payload={"identifier_type": "internal"},
            ean="4006381333931",
            status="loaded",
            product_source_id=source.id,
        )
    ]

    suggestions, conflicts = _gtin_suggestions(
        evidence=evidence,
        sources_by_id={source.id: source},
    )

    assert suggestions == []
    assert conflicts == []
