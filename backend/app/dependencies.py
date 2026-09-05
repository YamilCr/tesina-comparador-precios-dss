"""Dependencias de FastAPI que conectarán los adaptadores con la aplicación."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.modules.catalog.domain.ports import ProductSearchIndexPort
from app.modules.catalog.infrastructure.search import ChromaProductSearchIndex
from app.shared.infrastructure.database import async_session_factory
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """Crea una unidad de trabajo para futuros casos de uso o dependencias HTTP."""
    return SQLAlchemyUnitOfWork(async_session_factory)


@lru_cache
def get_product_search_index() -> ProductSearchIndexPort | None:
    """Returns the configured product search index, if semantic search is enabled."""
    settings = get_settings()
    if not settings.vector_search_enabled:
        return None
    return ChromaProductSearchIndex(
        path=settings.vector_store_path,
        collection_name=settings.vector_collection,
        embedding_model=settings.vector_embedding_model,
    )


ProductSearchIndexDependency = Annotated[
    ProductSearchIndexPort | None,
    Depends(get_product_search_index),
]
