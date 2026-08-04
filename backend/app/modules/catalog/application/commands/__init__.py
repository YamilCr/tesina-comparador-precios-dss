"""Queries y comandos de aplicación del módulo de catálogo."""

from .list_products_query import ProductListQuery
from .search_products_query import SearchProductsQuery

ProductSearchQuery = SearchProductsQuery

__all__ = ["ProductListQuery", "ProductSearchQuery", "SearchProductsQuery"]
