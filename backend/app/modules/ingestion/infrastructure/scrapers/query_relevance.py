"""Deterministic relevance checks for broad supermarket search responses."""

import re
import unicodedata


QUERY_STOP_WORDS = frozenset({"a", "al", "con", "de", "del", "el", "en", "la", "las", "los", "para", "por", "sin", "un", "una", "y"})


def matches_query(*, query: str, name: str, brand: str | None = None) -> bool:
    """Requires every meaningful query token to appear in the name or brand."""
    required_tokens = _tokens(query) - QUERY_STOP_WORDS
    if not required_tokens:
        return True
    candidate_tokens = _tokens(" ".join(part for part in (name, brand) if part))
    return required_tokens.issubset(candidate_tokens)


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    return set(re.findall(r"[a-z]+|\d+(?:\.\d+)?", normalized))
