"""Quality rules for staged extracted products."""

from app.modules.ingestion.domain.entities import ScrapedProduct

from .product_cleaner import clean_text


def validate_scraped_product(product: ScrapedProduct) -> list[str]:
    """Returns every deterministic quality issue without mutating the staged record."""
    issues: list[str] = []
    if clean_text(product.external_code) is None:
        issues.append("Missing external code.")
    elif len(product.external_code) > 255:
        issues.append("External code exceeds 255 characters.")
    if clean_text(product.name) is None:
        issues.append("Missing product name.")
    elif len(product.name) > 500:
        issues.append("Product name exceeds 500 characters.")
    return issues
