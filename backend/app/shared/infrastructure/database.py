"""Fábricas asíncronas de motor y sesión para la infraestructura de persistencia."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.shared.infrastructure.settings import Settings, get_settings


def create_database_engine(settings: Settings) -> AsyncEngine:
    """Crea un motor asíncrono a partir de la URL configurada."""
    return create_async_engine(settings.database_url)


async_engine = create_database_engine(get_settings())
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Proporciona una sesión asíncrona para dependencias de infraestructura futuras."""
    async with async_session_factory() as session:
        yield session
