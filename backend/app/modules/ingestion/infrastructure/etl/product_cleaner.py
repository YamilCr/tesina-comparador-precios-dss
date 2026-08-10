"""Small, deterministic cleanup helpers for extracted product text."""

import re


def clean_text(value: str | None) -> str | None:
    """Collapses whitespace and returns ``None`` for blank values."""
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None
