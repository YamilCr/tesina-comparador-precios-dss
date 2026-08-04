"""Helpers para construir respuestas HTTP consistentes."""

from typing import Any


def pagination_meta(page: int, page_size: int, total: int) -> dict[str, int]:
    """Construye metadatos de paginación estables para clientes HTTP."""
    return {
        "page": page,
        "page_size": page_size,
        "count": total,
        "total": total,
    }


def collection_response(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Construye una respuesta estándar para colecciones no paginadas."""
    return {
        "items": items,
        "count": len(items),
    }


def paginated_response(
    items: list[dict[str, Any]],
    *,
    page: int,
    page_size: int,
    total: int,
) -> dict[str, Any]:
    """Construye una respuesta estándar para colecciones paginadas."""
    return {
        "items": items,
        "count": len(items),
        "pagination": pagination_meta(page, page_size, total),
    }
