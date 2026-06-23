"""Dependencias de FastAPI que conectarán los adaptadores con la aplicación."""

from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.shared.infrastructure.database import async_session_factory
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_unit_of_work() -> SQLAlchemyUnitOfWork:
    """Crea una unidad de trabajo para futuros casos de uso o dependencias HTTP."""
    return SQLAlchemyUnitOfWork(async_session_factory)
