"""Normalize optional scraper image links without rejecting valid prices."""

from urllib.parse import urljoin, urlsplit


def normalize_image_url(value: object, product_url: str | None = None) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        url = urljoin(product_url or "", value.strip())
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or len(url) > 2048
            or any(character.isspace() or ord(character) < 32 for character in url)
        ):
            return None
        return url
    except ValueError:
        return None
