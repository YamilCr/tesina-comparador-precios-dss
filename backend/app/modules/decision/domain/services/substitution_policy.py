"""Conservative purchase substitutions, independent of canonical identity matching."""

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal

from rapidfuzz.distance import Levenshtein

from app.modules.catalog.domain.entities import Product


UNITS = {
    "kg": ("g", 1000),
    "kgs": ("g", 1000),
    "kilo": ("g", 1000),
    "kilos": ("g", 1000),
    "g": ("g", 1),
    "gr": ("g", 1),
    "grs": ("g", 1),
    "gramo": ("g", 1),
    "gramos": ("g", 1),
    "l": ("ml", 1000),
    "lt": ("ml", 1000),
    "lts": ("ml", 1000),
    "litro": ("ml", 1000),
    "litros": ("ml", 1000),
    "ml": ("ml", 1),
    "cc": ("ml", 1),
    "cm3": ("ml", 1),
    "u": ("unit", 1),
    "un": ("unit", 1),
    "unidad": ("unit", 1),
    "unidades": ("unit", 1),
    "unit": ("unit", 1),
}
UNIT_PATTERN = "|".join(sorted(UNITS, key=len, reverse=True))
QUANTITY = re.compile(rf"(?<!\w)(\d+(?:\.\d+)?)\s*({UNIT_PATTERN})\b")
PACK = re.compile(
    r"\bpack\s*(?:x\s*)?(\d+)\b|\bx\s*(\d+)\b(?![.\d])(?!\s*(?:" + UNIT_PATTERN + r")\b)"
)
COUNTS = re.compile(r"\b(\d+)\s*(?:unidades|unidad|un|u)\b")
ARTICLES = {"de", "del", "el", "la", "los", "las", "en"}


def normalized_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold()).replace(",", ".").replace("\u200b", "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\bc\s*/\s*", "con ", text)
    return re.sub(r"\bs\s*/\s*", "sin ", text)


def _internal_typo(left: str, right: str) -> bool:
    # Only one inserted/omitted internal letter, not arbitrary fuzzy similarity.
    return (
        left.isalpha()
        and right.isalpha()
        and min(len(left), len(right)) >= 8
        and abs(len(left) - len(right)) == 1
        and left[:3] == right[:3]
        and left[-3:] == right[-3:]
        and Levenshtein.distance(left, right, score_cutoff=1) == 1
    )


def _plural_pair(left: str, right: str) -> bool:
    short, long = sorted((left, right), key=len)
    if not short.isalpha() or len(short) < 4:
        return False
    return long == short + ("s" if short[-1] in "aeiou" else "es")


def _compatible_descriptors(left: frozenset[str], right: frozenset[str]) -> bool:
    unmatched_left, unmatched_right = left - right, right - left
    if len(unmatched_left) != len(unmatched_right):
        return False
    used, typo_count = set(), 0
    for word in sorted(unmatched_left):
        matches = [
            other
            for other in unmatched_right
            if _plural_pair(word, other) or _internal_typo(word, other)
        ]
        if len(matches) != 1 or matches[0] in used:
            return False
        used.add(matches[0])
        typo_count += not _plural_pair(word, matches[0])
    # Added/dropped qualifiers, numbers and short negations must remain exact.
    return typo_count <= 1


@dataclass(frozen=True)
class SubstitutionSignature:
    amount: Decimal
    unit: str
    pack: int
    tokens: frozenset[str]


def signature(product: Product, brand: str | None) -> SubstitutionSignature | None:
    text = normalized_text(product.normalized_name + " " + (product.description or ""))
    # Remove only the explicit brand phrase, never arbitrary words inferred as a brand.
    if brand:
        brand_tokens = re.findall(r"[a-z]+|\d+", normalized_text(brand))
        if brand_tokens:
            pattern = r"(?<!\w)" + r"[\W_]*".join(map(re.escape, brand_tokens)) + r"(?!\w)"
            brand_found = re.search(pattern, text) is not None
            text = re.sub(pattern, " ", text)
            if not brand_found and len(brand_tokens) == 1:
                misspellings = {
                    word
                    for word in re.findall(r"[a-z]+", text)
                    if _internal_typo(word, brand_tokens[0])
                }
                if len(misspellings) == 1:
                    text = re.sub(r"\b" + re.escape(misspellings.pop()) + r"\b", " ", text)
    packs = {int(a or b) for a, b in PACK.findall(text)}
    packs.update(int(n) for n in COUNTS.findall(text))
    if len(packs) > 1 or any(n < 1 for n in packs):
        return None
    without_pack = PACK.sub(" ", text)
    without_pack = re.sub(rf"\bx\s*(?=\d+(?:\.\d+)?\s*(?:{UNIT_PATTERN})\b)", " ", without_pack)
    # A unit count alongside weight/volume describes the pack, not a second net quantity.
    if re.search(
        rf"\d\s*(?:{'|'.join(u for u, base in UNITS.items() if base[0] != 'unit')})\b", without_pack
    ):
        without_pack = COUNTS.sub(" ", without_pack)
    quantities = {
        (Decimal(amount) * UNITS[unit][1], UNITS[unit][0])
        for amount, unit in QUANTITY.findall(without_pack)
    }
    if product.unit_measure and product.net_content is not None:
        unit = UNITS.get(normalized_text(product.unit_measure))
        if unit is None:
            return None
        quantities.add((product.net_content * unit[1], unit[0]))
    if len(quantities) != 1:
        return None
    amount, unit = next(iter(quantities))
    if amount <= 0:
        return None
    residual = QUANTITY.sub(" ", without_pack)
    tokens = frozenset(re.findall(r"[a-z]+|\d+(?:\.\d+)?%?", residual)) - ARTICLES
    # An unresolved multiplier/pack marker is ambiguous, not evidence of a single unit.
    if not tokens or tokens & {"pack", "packs", "x", "paq", "paquete", "paquetes"}:
        return None
    return SubstitutionSignature(amount, unit, next(iter(packs), 1), tokens)


def compatible(
    original: Product, replacement: Product, original_brand=None, replacement_brand=None
) -> bool:
    if original.id == replacement.id or not original.active or not replacement.active:
        return False
    if (
        original.category_id
        and replacement.category_id
        and original.category_id != replacement.category_id
    ):
        return False
    left, right = signature(original, original_brand), signature(replacement, replacement_brand)
    return (
        left is not None
        and right is not None
        and (left.amount, left.unit, left.pack) == (right.amount, right.unit, right.pack)
        and _compatible_descriptors(left.tokens, right.tokens)
    )
