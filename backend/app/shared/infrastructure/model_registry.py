"""Registro de modelos SQLAlchemy para la detección de metadata por Alembic."""

from app.modules.catalog.infrastructure.persistence import (
    BrandModel,
    ProductCategoryModel,
    ProductModel,
    ProductSourceModel,
)
from app.modules.prices.infrastructure.persistence import PriceModel
from app.modules.supermarkets.infrastructure.persistence import (
    BranchModel,
    CityModel,
    ProvinceModel,
    SupermarketModel,
)

__all__ = [
    "BranchModel",
    "BrandModel",
    "CityModel",
    "PriceModel",
    "ProductCategoryModel",
    "ProductModel",
    "ProductSourceModel",
    "ProvinceModel",
    "SupermarketModel",
]
