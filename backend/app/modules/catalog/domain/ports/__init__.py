"""Puertos de persistencia requeridos por el dominio de catálogo."""

from .brand_repository_port import BrandRepositoryPort
from .product_category_repository_port import ProductCategoryRepositoryPort
from .product_repository_port import ProductRepositoryPort
from .product_source_repository_port import ProductSourceRepositoryPort

__all__ = [
    "BrandRepositoryPort",
    "ProductCategoryRepositoryPort",
    "ProductRepositoryPort",
    "ProductSourceRepositoryPort",
]
