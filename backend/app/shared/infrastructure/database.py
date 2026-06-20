"""Fábricas de conexión para los adaptadores de persistencia futuros."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.shared.infrastructure.settings import Settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    """Crea el motor asíncrono sin definir modelos ni operaciones de datos."""
    return create_async_engine(settings.database_url)
