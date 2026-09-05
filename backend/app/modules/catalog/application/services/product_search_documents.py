"""Builds E5-formatted documents for product search vectors."""

from decimal import Decimal

from app.modules.catalog.domain.entities import Product
from app.modules.catalog.domain.ports import ProductSearchIndexEntry


def build_product_search_query(query: str) -> str:
    """Formats user text with the query prefix expected by E5 models."""
    return f"query: {query.strip()}"


def build_product_search_entry(
    product: Product,
    *,
    brand_name: str | None = None,
    category_name: str | None = None,
) -> ProductSearchIndexEntry:
    """Builds the vector document and searchable metadata for one product."""
    net_content = _format_decimal(product.net_content)
    unit_measure = product.unit_measure or ""
    internal_code = product.internal_code or ""
    document = (
        f"passage: producto {product.normalized_name}. "
        f"marca {brand_name or ''}. "
        f"categoria {category_name or ''}. "
        f"presentacion {net_content} {unit_measure}. "
        f"codigo {internal_code}"
    )
    return ProductSearchIndexEntry(
        product_id=product.id,
        document=" ".join(document.split()),
        metadata={
            "product_id": str(product.id),
            "normalized_name": product.normalized_name,
            "brand": brand_name,
            "category": category_name,
            "unit_measure": product.unit_measure,
            "net_content": float(product.net_content) if product.net_content is not None else None,
            "internal_code": product.internal_code,
            "active": product.active,
        },
    )


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    normalized = value.normalize()
    return format(normalized, "f")
