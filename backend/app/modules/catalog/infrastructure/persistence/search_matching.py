"""Token-based matching for normalized product catalog searches."""

import re
import unicodedata


def matches_product_name_query(*, name: str, query: str) -> bool:
    """Matches complete normalized query terms, never arbitrary substrings."""
    query_tokens = _tokens(query)
    return bool(query_tokens) and query_tokens.issubset(_tokens(name))


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return set(re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalized))
