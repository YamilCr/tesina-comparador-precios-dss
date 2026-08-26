"""Unit tests for conservative cross-supermarket product identity."""

from decimal import Decimal
from uuid import uuid4

from app.modules.catalog.domain.entities import Product
from app.modules.ingestion.infrastructure.etl import (
    PackageQuantity,
    ProductIdentityCandidate,
    ProductIdentityMatcher,
    extract_package_quantity,
    normalize_gtin,
)


def _candidate(
    name: str,
    *,
    brand: str | None = None,
    unit: str | None = None,
    content: Decimal | None = None,
) -> ProductIdentityCandidate:
    return ProductIdentityCandidate(
        product=Product(
            id=uuid4(),
            normalized_name=name,
            unit_measure=unit,
            net_content=content,
        ),
        brand_name=brand,
    )


def test_equivalent_volume_presentations_share_one_base_quantity() -> None:
    expected = PackageQuantity(amount=Decimal("2250"), unit="ml")

    assert extract_package_quantity("2,25 Lt.") == expected
    assert extract_package_quantity("2250cm3") == expected
    assert extract_package_quantity("2250 ml") == expected


def test_matches_equivalent_name_brand_and_presentation() -> None:
    candidate = _candidate(
        "Coca Cola 2.25 L",
        brand="Coca Cola",
        unit="L",
        content=Decimal("2.25"),
    )

    match = ProductIdentityMatcher().match(
        name="Gaseosa Coca-Cola sabor original descartable 2250cm3",
        presentation="2250 cm3",
        brand="Coca Cola",
        candidates=[candidate],
    )

    assert match is not None
    assert match.product.id == candidate.product.id
    assert match.confidence >= Decimal("0.900")


def test_does_not_match_different_size_brand_or_variant() -> None:
    coca = _candidate(
        "Coca Cola 2.25 L",
        brand="Coca Cola",
        unit="L",
        content=Decimal("2.25"),
    )
    zero = _candidate(
        "Coca Cola Zero 2.25 L",
        brand="Coca Cola",
        unit="L",
        content=Decimal("2.25"),
    )
    matcher = ProductIdentityMatcher()

    assert (
        matcher.match(
            name="Coca Cola 2.5 L",
            presentation="2.5 L",
            brand="Coca Cola",
            candidates=[coca],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola 2.25 L",
            presentation="2.25 L",
            brand="Pepsi",
            candidates=[coca],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola Zero 2.25 L",
            presentation="2.25 L",
            brand="Coca Cola",
            candidates=[coca],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola 2.25 L",
            presentation="2.25 L",
            brand="Coca Cola",
            candidates=[zero],
        )
        is None
    )


def test_ambiguous_canonical_candidates_are_not_merged() -> None:
    candidates = [
        _candidate("Coca Cola 2.25 L", brand="Coca Cola"),
        _candidate("Coca-Cola 2250 ml", brand="Coca Cola"),
    ]

    match = ProductIdentityMatcher().match(
        name="Gaseosa Coca Cola 2.25 L",
        presentation="2.25 L",
        brand="Coca Cola",
        candidates=candidates,
    )

    assert match is None


def test_only_checksum_valid_gtins_are_accepted() -> None:
    assert normalize_gtin("4006381333931") == "4006381333931"
    assert normalize_gtin("4006381333931", identifier_type="gtin") == "4006381333931"
    assert normalize_gtin("4006381333931", identifier_type="internal") is None
    assert normalize_gtin("4006381333932") is None
    assert normalize_gtin("internal-12345") is None
