"""Normalization used for conservative matching between supermarket sources."""

import re
import unicodedata
from dataclasses import dataclass

from .product_cleaner import clean_text


STOP_WORDS = frozenset({"con", "de", "del", "el", "la", "los", "las", "sabor", "original", "gaseosa"})
UNIT_ALIASES = {
    "lt": "l",
    "lts": "l",
    "litro": "l",
    "litros": "l",
    "cc": "cm3",
    "cm3": "cm3",
    "gr": "g",
    "grs": "g",
    "gramo": "g",
    "gramos": "g",
    "kilo": "kg",
    "kilos": "kg",
}


@dataclass(frozen=True)
class NormalizedProduct:
    """Carries display text and a stable token key for exact semantic matching."""

    name: str
    matching_key: str
    original_unit: str | None


def normalize_product(name: str, presentation: str | None = None) -> NormalizedProduct:
    """Normalizes a source name without guessing categories or brands."""
    cleaned_name = clean_text(name)
    if cleaned_name is None:
        raise ValueError("Missing product name.")
    cleaned_presentation = clean_text(presentation)
    return NormalizedProduct(
        name=cleaned_name,
        matching_key=product_matching_key(cleaned_name),
        original_unit=cleaned_presentation,
    )


def product_matching_key(value: str) -> str:
    """Builds a case- and accent-insensitive key suitable for exact token-set matching."""
    ascii_value = unicodedata.normalize("NFKD", value.casefold())
    ascii_value = "".join(character for character in ascii_value if not unicodedata.combining(character))
    ascii_value = re.sub(r"(\d)(cm3|ml|lts?|litros?|kg|grs?|g)\b", r"\1 \2", ascii_value)
    tokens = re.findall(r"[a-z]+|\d+(?:\.\d+)?", ascii_value)
    normalized_tokens = [UNIT_ALIASES.get(token, token) for token in tokens]
    meaningful_tokens = sorted({token for token in normalized_tokens if token not in STOP_WORDS})
    return " ".join(meaningful_tokens)
