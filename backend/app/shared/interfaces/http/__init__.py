"""Utilidades compartidas para la interfaz HTTP."""

from .error_handlers import register_error_handlers
from .responses import collection_response, paginated_response, pagination_meta

__all__ = [
    "collection_response",
    "paginated_response",
    "pagination_meta",
    "register_error_handlers",
]
