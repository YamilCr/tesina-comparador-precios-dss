"""Contrato transaccional independiente de la infraestructura de persistencia."""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self

from app.modules.catalog.domain.ports import (
    BrandRepositoryPort,
    ProductCategoryRepositoryPort,
    ProductRepositoryPort,
    ProductSourceRepositoryPort,
)
from app.modules.prices.domain.ports import PriceRepositoryPort
from app.modules.supermarkets.domain.ports import (
    BranchRepositoryPort,
    CityRepositoryPort,
    ProvinceRepositoryPort,
    SupermarketRepositoryPort,
)


class UnitOfWorkPort(ABC):
    """Define repositorios y ciclo transaccional sin depender de un ORM."""

    @property
    @abstractmethod
    def provinces(self) -> ProvinceRepositoryPort:
        """Expone el puerto de provincias asociado a la transacción."""

    @property
    @abstractmethod
    def cities(self) -> CityRepositoryPort:
        """Expone el puerto de ciudades asociado a la transacción."""

    @property
    @abstractmethod
    def supermarkets(self) -> SupermarketRepositoryPort:
        """Expone el puerto de supermercados asociado a la transacción."""

    @property
    @abstractmethod
    def branches(self) -> BranchRepositoryPort:
        """Expone el puerto de sucursales asociado a la transacción."""

    @property
    @abstractmethod
    def product_categories(self) -> ProductCategoryRepositoryPort:
        """Expone el puerto de categorías asociado a la transacción."""

    @property
    @abstractmethod
    def brands(self) -> BrandRepositoryPort:
        """Expone el puerto de marcas asociado a la transacción."""

    @property
    @abstractmethod
    def products(self) -> ProductRepositoryPort:
        """Expone el puerto de productos asociado a la transacción."""

    @property
    @abstractmethod
    def product_sources(self) -> ProductSourceRepositoryPort:
        """Expone el puerto de productos fuente asociado a la transacción."""

    @property
    @abstractmethod
    def prices(self) -> PriceRepositoryPort:
        """Expone el puerto de precios asociado a la transacción."""

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Inicia el contexto transaccional."""

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Finaliza el contexto transaccional."""

    @abstractmethod
    async def commit(self) -> None:
        """Confirma el trabajo realizado."""

    @abstractmethod
    async def rollback(self) -> None:
        """Revierte el trabajo realizado."""


UnitOfWork = UnitOfWorkPort
