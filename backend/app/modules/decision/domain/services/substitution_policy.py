"""Conservative purchase substitutions, independent of canonical identity matching."""

import re
import unicodedata
from collections.abc import Iterable
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
PROTECTED_BRAND_WORDS = {
    "sin",
    "con",
    "gluten",
    "lactosa",
    "azucar",
    "integral",
    "light",
    "zero",
    "original",
    "descremada",
    "entera",
    "parboil",
    "parboilizado",
}
RICE_LONG_REFINEMENTS = {"fino", "00000"}


def normalized_text(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold()).replace(",", ".").replace("\u200b", "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\bc\s*/\s*", "con ", text)
    return re.sub(r"\bs\s*/\s*", "sin ", text)


def known_brand_aliases(names: Iterable[str]) -> tuple[str, ...]:
    """Recognize complete known brand names and conservative manufacturer aliases."""
    aliases = set()
    for name in names:
        words = re.findall(r"[a-z]+|\d+", normalized_text(name))
        if len(words) >= 2 and not set(words) & PROTECTED_BRAND_WORDS:
            aliases.add(" ".join(words))
            if len(words) == 2 and words[0] == "molinos" and len(words[1]) >= 3:
                aliases.add(words[1])
    return tuple(sorted(aliases, key=lambda value: (-len(value.split()), -len(value), value)))


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


def signature(
    product: Product, brand: str | None, aliases: tuple[str, ...] = ()
) -> SubstitutionSignature | None:
    text = _descriptor_text(product.normalized_name + " " + (product.description or ""), brand, aliases)
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


def _descriptor_text(value: str, brand: str | None, aliases: tuple[str, ...]) -> str:
    text = normalized_text(value)
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
    for alias in aliases:
        words = alias.split()
        pattern = r"(?<!\w)" + r"[\W_]*".join(map(re.escape, words)) + r"(?!\w)"
        text = re.sub(pattern, " ", text)
    return text


def product_family(product: Product, brand: str | None, aliases: tuple[str, ...] = ()) -> str | None:
    text = _descriptor_text(product.normalized_name, brand, aliases)
    text = PACK.sub(" ", QUANTITY.sub(" ", text))
    words = re.findall(r"[a-z]+", text)
    return next((word for word in words if word not in ARTICLES and word not in UNITS and len(word) >= 3), None)


def similar_product(
    original: Product,
    replacement: Product,
    original_brand: str | None = None,
    replacement_brand: str | None = None,
    *,
    known_brands: tuple[str, ...] = (),
) -> bool:
    if original.id == replacement.id or not original.active or not replacement.active:
        return False
    if original.category_id and replacement.category_id and original.category_id != replacement.category_id:
        return False
    left = product_family(original, original_brand, known_brands)
    right = product_family(replacement, replacement_brand, known_brands)
    return bool(left and right and (left == right or _plural_pair(left, right) or _internal_typo(left, right)))


def compatible(
    original: Product,
    replacement: Product,
    original_brand=None,
    replacement_brand=None,
    *,
    known_brands: tuple[str, ...] = (),
) -> bool:
    if original.id == replacement.id or not original.active or not replacement.active:
        return False
    if (
        original.category_id
        and replacement.category_id
        and original.category_id != replacement.category_id
    ):
        return False
    left = signature(original, original_brand, known_brands)
    right = signature(replacement, replacement_brand, known_brands)
    if left is None or right is None:
        return False
    if (left.amount, left.unit, left.pack) != (right.amount, right.unit, right.pack):
        return False
    if _compatible_descriptors(left.tokens, right.tokens):
        return True
    original_head = re.findall(r"[a-z]+", normalized_text(original.normalized_name))[:1]
    replacement_head = re.findall(r"[a-z]+", normalized_text(replacement.normalized_name))[:1]
    return (
        original_head == replacement_head == ["arroz"]
        and {"arroz", "largo"} <= left.tokens & right.tokens
        and _compatible_descriptors(
            left.tokens - RICE_LONG_REFINEMENTS,
            right.tokens - RICE_LONG_REFINEMENTS,
        )
    )
