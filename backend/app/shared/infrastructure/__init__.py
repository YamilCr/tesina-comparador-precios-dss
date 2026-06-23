"""Adaptadores técnicos compartidos para configuración, persistencia y observabilidad."""

from .database import async_session_factory, get_async_session
from .sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

__all__ = ["SQLAlchemyUnitOfWork", "async_session_factory", "get_async_session"]
