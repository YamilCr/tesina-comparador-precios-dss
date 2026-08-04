"""Aliases de compatibilidad para DTOs de localización."""

from app.modules.supermarkets.application.commands import ListBranchesQuery

from .branch_dto import BranchDTO
from .city_dto import CityDTO
from .province_dto import ProvinceDTO
from .supermarket_dto import SupermarketDTO

__all__ = [
    "BranchDTO",
    "CityDTO",
    "ListBranchesQuery",
    "ProvinceDTO",
    "SupermarketDTO",
]
