"""Puertos de persistencia requeridos por el dominio de supermercados."""

from .branch_repository_port import BranchRepositoryPort
from .city_repository_port import CityRepositoryPort
from .province_repository_port import ProvinceRepositoryPort
from .supermarket_repository_port import SupermarketRepositoryPort

__all__ = [
    "BranchRepositoryPort",
    "CityRepositoryPort",
    "ProvinceRepositoryPort",
    "SupermarketRepositoryPort",
]
