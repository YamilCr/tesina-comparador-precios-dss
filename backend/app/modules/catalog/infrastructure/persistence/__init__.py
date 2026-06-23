"""Modelos SQLAlchemy del catálogo normalizado y sus fuentes externas."""

from .sqlalchemy_models import BrandModel, ProductCategoryModel, ProductModel, ProductSourceModel
from .sqlalchemy_brand_repository import SQLAlchemyBrandRepository
from .sqlalchemy_product_category_repository import SQLAlchemyProductCategoryRepository
from .sqlalchemy_product_repository import SQLAlchemyProductRepository
from .sqlalchemy_product_source_repository import SQLAlchemyProductSourceRepository

__all__ = [
    "BrandModel",
    "ProductCategoryModel",
    "ProductModel",
    "ProductSourceModel",
    "SQLAlchemyBrandRepository",
    "SQLAlchemyProductCategoryRepository",
    "SQLAlchemyProductRepository",
    "SQLAlchemyProductSourceRepository",
]
