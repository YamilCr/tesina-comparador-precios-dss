"""Implementación SQLAlchemy asíncrona de la unidad de trabajo compartida."""

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.catalog.infrastructure.persistence import (
    SQLAlchemyBrandRepository,
    SQLAlchemyProductCategoryRepository,
    SQLAlchemyProductRepository,
    SQLAlchemyProductSourceRepository,
)
from app.modules.prices.infrastructure.persistence import SQLAlchemyPriceRepository
from app.modules.supermarkets.infrastructure.persistence import (
    SQLAlchemyBranchRepository,
    SQLAlchemyCityRepository,
    SQLAlchemyProvinceRepository,
    SQLAlchemySupermarketRepository,
)
from app.shared.application.unit_of_work import UnitOfWorkPort


class SQLAlchemyUnitOfWork(UnitOfWorkPort):
    """Coordina sesión, repositorios y transacción mediante SQLAlchemy asíncrono."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Recibe la fábrica de sesiones configurada por la infraestructura."""
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._provinces: SQLAlchemyProvinceRepository | None = None
        self._cities: SQLAlchemyCityRepository | None = None
        self._supermarkets: SQLAlchemySupermarketRepository | None = None
        self._branches: SQLAlchemyBranchRepository | None = None
        self._product_categories: SQLAlchemyProductCategoryRepository | None = None
        self._brands: SQLAlchemyBrandRepository | None = None
        self._products: SQLAlchemyProductRepository | None = None
        self._product_sources: SQLAlchemyProductSourceRepository | None = None
        self._prices: SQLAlchemyPriceRepository | None = None

    @property
    def session(self) -> AsyncSession:
        """Devuelve la sesión abierta o informa que el contexto no fue iniciado."""
        if self._session is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._session

    @property
    def provinces(self) -> SQLAlchemyProvinceRepository:
        """Expone el repositorio de provincias de la transacción actual."""
        if self._provinces is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._provinces

    @property
    def cities(self) -> SQLAlchemyCityRepository:
        """Expone el repositorio de ciudades de la transacción actual."""
        if self._cities is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._cities

    @property
    def supermarkets(self) -> SQLAlchemySupermarketRepository:
        """Expone el repositorio de supermercados de la transacción actual."""
        if self._supermarkets is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._supermarkets

    @property
    def branches(self) -> SQLAlchemyBranchRepository:
        """Expone el repositorio de sucursales de la transacción actual."""
        if self._branches is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._branches

    @property
    def product_categories(self) -> SQLAlchemyProductCategoryRepository:
        """Expone el repositorio de categorías de la transacción actual."""
        if self._product_categories is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._product_categories

    @property
    def brands(self) -> SQLAlchemyBrandRepository:
        """Expone el repositorio de marcas de la transacción actual."""
        if self._brands is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._brands

    @property
    def products(self) -> SQLAlchemyProductRepository:
        """Expone el repositorio de productos de la transacción actual."""
        if self._products is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._products

    @property
    def product_sources(self) -> SQLAlchemyProductSourceRepository:
        """Expone el repositorio de productos fuente de la transacción actual."""
        if self._product_sources is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._product_sources

    @property
    def prices(self) -> SQLAlchemyPriceRepository:
        """Expone el repositorio de precios de la transacción actual."""
        if self._prices is None:
            raise RuntimeError("Unit of work has not been entered.")
        return self._prices

    async def __aenter__(self) -> Self:
        """Abre una sesión e instancia los repositorios que comparten transacción."""
        self._session = self._session_factory()
        self._provinces = SQLAlchemyProvinceRepository(self._session)
        self._cities = SQLAlchemyCityRepository(self._session)
        self._supermarkets = SQLAlchemySupermarketRepository(self._session)
        self._branches = SQLAlchemyBranchRepository(self._session)
        self._product_categories = SQLAlchemyProductCategoryRepository(self._session)
        self._brands = SQLAlchemyBrandRepository(self._session)
        self._products = SQLAlchemyProductRepository(self._session)
        self._product_sources = SQLAlchemyProductSourceRepository(self._session)
        self._prices = SQLAlchemyPriceRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Revierte ante errores, cierra la sesión y deja propagar excepciones."""
        if self._session is None:
            return

        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()
            self._session = None
            self._provinces = None
            self._cities = None
            self._supermarkets = None
            self._branches = None
            self._product_categories = None
            self._brands = None
            self._products = None
            self._product_sources = None
            self._prices = None

    async def commit(self) -> None:
        """Confirma explícitamente la transacción abierta."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Revierte explícitamente la transacción abierta."""
        await self.session.rollback()
