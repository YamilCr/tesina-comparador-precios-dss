"""Dependencias de FastAPI que conectarán los adaptadores con la aplicación."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.modules.catalog.domain.ports import ProductSearchIndexPort
from app.modules.catalog.infrastructure.search import PgVectorProductSearchIndex
from app.shared.infrastructure.database import async_session_factory
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """Crea una unidad de trabajo para futuros casos de uso o dependencias HTTP."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@lru_cache
def get_product_search_index() -> ProductSearchIndexPort | None:
    """Returns the PostgreSQL-backed product search index when enabled."""
    settings = get_settings()
    if not settings.vector_search_enabled:
        return None
    return PgVectorProductSearchIndex(
        session_factory=async_session_factory,
        embedding_model=settings.vector_embedding_model,
        embedding_dimensions=settings.vector_embedding_dimensions,
    )


ProductSearchIndexDependency = Annotated[
    ProductSearchIndexPort | None,
    Depends(get_product_search_index),
]
