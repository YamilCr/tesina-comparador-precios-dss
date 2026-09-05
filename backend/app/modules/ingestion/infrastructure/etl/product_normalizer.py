"""Conservative normalization primitives for cross-supermarket product identity."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .product_cleaner import clean_text


STOP_WORDS = frozenset(
    {
        "con",
        "botella",
        "descartable",
        "de",
        "del",
        "el",
        "en",
        "envase",
        "gaseosa",
        "la",
        "las",
        "los",
        "original",
        "pack",
        "packs",
        "paq",
        "paquete",
        "paquetes",
        "pet",
        "rollo",
        "rollos",
        "sabor",
        "u",
        "ud",
        "uds",
        "un",
        "unidad",
        "unidades",
        "x",
    }
)
UNIT_ALIASES = {
    "cc": ("ml", Decimal("1")),
    "cm3": ("ml", Decimal("1")),
    "gr": ("g", Decimal("1")),
    "grs": ("g", Decimal("1")),
    "gramo": ("g", Decimal("1")),
    "gramos": ("g", Decimal("1")),
    "g": ("g", Decimal("1")),
    "kg": ("g", Decimal("1000")),
    "kilo": ("g", Decimal("1000")),
    "kilos": ("g", Decimal("1000")),
    "l": ("ml", Decimal("1000")),
    "lt": ("ml", Decimal("1000")),
    "lts": ("ml", Decimal("1000")),
    "litro": ("ml", Decimal("1000")),
    "litros": ("ml", Decimal("1000")),
    "ml": ("ml", Decimal("1")),
    "pack": ("unit", Decimal("1")),
    "paq": ("unit", Decimal("1")),
    "rollo": ("unit", Decimal("1")),
    "rollos": ("unit", Decimal("1")),
    "u": ("unit", Decimal("1")),
    "ud": ("unit", Decimal("1")),
    "uds": ("unit", Decimal("1")),
    "un": ("unit", Decimal("1")),
    "unidad": ("unit", Decimal("1")),
    "unidades": ("unit", Decimal("1")),
}
_UNIT_PATTERN = "|".join(sorted((re.escape(unit) for unit in UNIT_ALIASES), key=len, reverse=True))
_QUANTITY_PATTERN = re.compile(rf"(?<!\w)(\d+(?:\.\d+)?)\s*({_UNIT_PATTERN})\b")
_PACK_WORD_PATTERN = re.compile(r"\b(?:pack|packs|paq|paquete|paquetes)\s*(?:x|por)?\s*(\d+)\b")
_PACK_MULTIPLIER_PATTERN = re.compile(
    rf"\bx\s*(\d+)\b(?!\s*[.,]\d)(?!\s*(?:{_UNIT_PATTERN})\b)"
)
_COUNT_UNIT_PATTERN = re.compile(
    r"\b(\d+)\s*(?:unidades|unidad|rollos|rollo|uds|ud|un|u)\b"
)


@dataclass(frozen=True)
class PackageQuantity:
    """Comparable net quantity expressed in a base measurement unit."""

    amount: Decimal
    unit: str


@dataclass(frozen=True)
class ProductIdentity:
    """Structured identity used only when every discriminating field agrees."""

    tokens: frozenset[str]
    quantity: PackageQuantity | None
    pack_size: int | None = None


@dataclass(frozen=True)
class NormalizedProduct:
    """Carries display text and deterministic identity attributes for ETL."""

    name: str
    matching_key: str
    original_unit: str | None
    identity: ProductIdentity


def normalize_product(name: str, presentation: str | None = None) -> NormalizedProduct:
    """Normalizes source text without making an automatic match decision."""
    cleaned_name = clean_text(name)
    if cleaned_name is None:
        raise ValueError("Missing product name.")
    cleaned_presentation = clean_text(presentation)
    return NormalizedProduct(
        name=cleaned_name,
        matching_key=product_matching_key(cleaned_name),
        original_unit=cleaned_presentation,
        identity=build_product_identity(cleaned_name, presentation=cleaned_presentation),
    )


def build_product_identity(
    name: str,
    *,
    presentation: str | None = None,
    unit_measure: str | None = None,
    net_content: Decimal | None = None,
) -> ProductIdentity:
    """Builds normalized tokens and package quantity from source or catalog fields."""
    quantity = _explicit_quantity(unit_measure, net_content)
    pack_size = _resolved_pack_size(name, presentation)
    if quantity is None and presentation:
        quantity = extract_package_quantity(presentation)
    if quantity is None:
        quantity = extract_package_quantity(name)
    return ProductIdentity(tokens=identity_tokens(name), quantity=quantity, pack_size=pack_size)


def product_matching_key(value: str) -> str:
    """Builds a stable exact-match key with normalized decimals and measurement units."""
    normalized = _ascii_text(value)
    identity = build_product_identity(normalized)
    quantity = identity.quantity
    tokens = identity.tokens
    parts = sorted(tokens)
    if quantity is not None:
        parts.append(f"quantity={_decimal_text(quantity.amount)}{quantity.unit}")
    if identity.pack_size is not None:
        parts.append(f"pack={identity.pack_size}")
    return " ".join(parts)


def identity_tokens(value: str) -> frozenset[str]:
    """Returns meaningful name tokens while preserving product variants."""
    normalized = _ascii_text(value)
    normalized = _QUANTITY_PATTERN.sub(" ", normalized)
    normalized = _PACK_WORD_PATTERN.sub(" ", normalized)
    normalized = _PACK_MULTIPLIER_PATTERN.sub(" ", normalized)
    normalized = _COUNT_UNIT_PATTERN.sub(" ", normalized)
    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalized)
    return frozenset(token for token in tokens if token not in STOP_WORDS)


def normalized_token_set(value: str | None) -> frozenset[str]:
    """Normalizes a brand or short label without product-specific stop words."""
    if not value:
        return frozenset()
    return frozenset(re.findall(r"[a-z]+|\d+", _ascii_text(value)))


def normalized_brand_key(value: str | None) -> str:
    """Builds a punctuation-insensitive key for source brand consensus."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", _ascii_text(value))


def extract_package_quantity(value: str | None) -> PackageQuantity | None:
    """Extracts one unambiguous package quantity and converts it to a base unit."""
    if not value:
        return None
    matches: set[PackageQuantity] = set()
    for amount_text, unit_text in _QUANTITY_PATTERN.findall(_ascii_text(value)):
        try:
            amount = Decimal(amount_text)
        except InvalidOperation:
            continue
        if amount <= 0:
            continue
        base_unit, factor = UNIT_ALIASES[unit_text]
        matches.add(PackageQuantity(amount=(amount * factor).normalize(), unit=base_unit))
    return next(iter(matches)) if len(matches) == 1 else None


def extract_pack_size(value: str | None) -> int | None:
    """Extracts one unambiguous pack size without mistaking net content for packs."""
    if not value:
        return None
    normalized = _ascii_text(value)
    matches: set[int] = set()
    for pattern in (_PACK_WORD_PATTERN, _PACK_MULTIPLIER_PATTERN, _COUNT_UNIT_PATTERN):
        for amount_text in pattern.findall(normalized):
            amount = int(amount_text)
            if amount > 1:
                matches.add(amount)
    return next(iter(matches)) if len(matches) == 1 else None


def catalog_quantity_fields(
    quantity: PackageQuantity | None,
) -> tuple[str | None, Decimal | None]:
    """Converts a base quantity to the catalog's display unit and net content."""
    if quantity is None:
        return None, None
    if quantity.unit == "ml":
        return "L", quantity.amount / Decimal("1000")
    if quantity.unit == "g" and quantity.amount >= Decimal("1000"):
        return "KG", quantity.amount / Decimal("1000")
    if quantity.unit == "g":
        return "G", quantity.amount
    if quantity.unit == "unit":
        return "PACK", quantity.amount
    return None, None


def normalize_gtin(
    value: str | None,
    *,
    identifier_type: str | None = None,
) -> str | None:
    """Returns a checksum-valid GTIN-8/12/13/14, rejecting internal source codes."""
    if not value:
        return None
    if identifier_type is not None and identifier_type.strip().casefold() != "gtin":
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) not in {8, 12, 13, 14}:
        return None
    body, check_digit = digits[:-1], int(digits[-1])
    weighted_sum = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(body))
    )
    expected = (10 - weighted_sum % 10) % 10
    return digits if expected == check_digit else None


def _explicit_quantity(unit_measure: str | None, net_content: Decimal | None) -> PackageQuantity | None:
    if not unit_measure or net_content is None or net_content <= 0:
        return None
    normalized_unit = _ascii_text(unit_measure).strip()
    alias = UNIT_ALIASES.get(normalized_unit)
    if alias is None:
        return None
    base_unit, factor = alias
    return PackageQuantity(amount=(net_content * factor).normalize(), unit=base_unit)


def _resolved_pack_size(name: str, presentation: str | None) -> int | None:
    matches = {
        pack_size
        for pack_size in (extract_pack_size(name), extract_pack_size(presentation))
        if pack_size is not None
    }
    return next(iter(matches)) if len(matches) == 1 else None


def _ascii_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.casefold().replace("\u200b", ""))
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = re.sub(r"(?<=\d),(?=\d)", ".", normalized)
    return re.sub(r"[^a-z0-9.%]+", " ", normalized).strip()


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")
