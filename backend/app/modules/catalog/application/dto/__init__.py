"""Objetos de transferencia de datos usados por los casos de uso de catálogo."""

from app.modules.catalog.application.commands import ProductListQuery, ProductSearchQuery

from .brand_dto import BrandDTO
from .product_category_dto import ProductCategoryDTO
from .product_dto import ProductDTO

__all__ = [
    "BrandDTO",
    "ProductCategoryDTO",
    "ProductDTO",
    "ProductListQuery",
    "ProductSearchQuery",
]
