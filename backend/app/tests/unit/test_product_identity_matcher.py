"""Unit tests for conservative cross-supermarket product identity."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.catalog.domain.entities import Product
from app.modules.ingestion.infrastructure.etl import (
    PackageQuantity,
    ProductIdentityCandidate,
    ProductIdentityMatcher,
    build_product_identity,
    extract_pack_size,
    extract_package_quantity,
    normalize_gtin,
    product_matching_key,
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2,25 Lt.", PackageQuantity(amount=Decimal("2250"), unit="ml")),
        ("2250cm3", PackageQuantity(amount=Decimal("2250"), unit="ml")),
        ("2250 ml", PackageQuantity(amount=Decimal("2250"), unit="ml")),
        ("500 cc", PackageQuantity(amount=Decimal("500"), unit="ml")),
        ("1 kg", PackageQuantity(amount=Decimal("1000"), unit="g")),
        ("1000 g", PackageQuantity(amount=Decimal("1000"), unit="g")),
        ("2 un", PackageQuantity(amount=Decimal("2"), unit="unit")),
    ],
)
def test_equivalent_presentations_share_one_base_quantity(
    value: str,
    expected: PackageQuantity,
) -> None:
    assert extract_package_quantity(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Coca Cola 2.25 L Pack x2", 2),
        ("Coca Cola 2.25 L pack por 2", 2),
        ("Coca Cola 2.25 L x 2", 2),
        ("Jabon tocador 2 un", 2),
        ("Papel higienico 4 rollos", 4),
        ("COCA COLA SABOR ORIGINAL X 2.25 LTS", None),
        ("Fernet Branca x 750 cc", None),
        ("Coca Cola 1 unidad", None),
    ],
)
def test_extracts_pack_size_without_confusing_net_content(
    value: str,
    expected: int | None,
) -> None:
    assert extract_pack_size(value) == expected


def test_product_matching_key_preserves_pack_size_as_discriminator() -> None:
    single = product_matching_key("Coca Cola 2.25 L")
    multipack = product_matching_key("Coca Cola 2.25 L Pack x2")

    assert single != multipack
    assert "pack=2" in multipack


def test_original_is_compatible_but_sugar_free_variants_are_preserved() -> None:
    original = build_product_identity("Coca Cola Original 2.25L")
    sugar_free = build_product_identity("Coca Cola Sin Azúcar 2.25L")

    assert "original" not in original.tokens
    assert {"sin", "azucar"} <= sugar_free.tokens


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


@pytest.mark.parametrize(
    "name",
    [
        "Coca Cola Original 2.25L",
        "Gaseosa Coca-Cola 2,25 Lt",
        "COCA COLA SABOR ORIGINAL X 2.25 LTS",
        "CocaCola 2250ml",
    ],
)
def test_matches_common_coca_cola_equivalent_spellings(name: str) -> None:
    candidate = _candidate(
        "Coca Cola 2.25 L",
        brand="Coca Cola",
        unit="L",
        content=Decimal("2.25"),
    )

    match = ProductIdentityMatcher().match(
        name=name,
        presentation=None,
        brand=None,
        candidates=[candidate],
    )

    assert match is not None
    assert match.product.id == candidate.product.id
    assert match.confidence >= Decimal("0.899")


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
    pack = _candidate(
        "Coca Cola 2.25 L Pack x2",
        brand="Coca Cola",
        unit="L",
        content=Decimal("2.25"),
    )
    sancor_milk = _candidate(
        "Leche Entera Sancor 1L",
        brand="Sancor",
        unit="L",
        content=Decimal("1"),
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
            presentation="1.5 L",
            brand="Coca Cola",
            candidates=[coca],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola 1.5 L",
            presentation="1.5 L",
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
            name="Coca Cola Sin Azúcar 2.25 L",
            presentation="2.25 L",
            brand="Coca Cola",
            candidates=[zero],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola 2.25 L",
            presentation="2.25 L",
            brand="Coca Cola",
            candidates=[pack],
        )
        is None
    )
    assert (
        matcher.match(
            name="Coca Cola 2.25 L Pack x2",
            presentation="2.25 L",
            brand="Coca Cola",
            candidates=[coca],
        )
        is None
    )
    assert (
        matcher.match(
            name="Leche Entera La Serenisima 1L",
            presentation="1 L",
            brand="La Serenisima",
            candidates=[sancor_milk],
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
