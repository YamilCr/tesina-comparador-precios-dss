"""Adaptadores tecnicos compartidos para configuracion, persistencia y observabilidad."""

__all__ = ["SQLAlchemyUnitOfWork", "async_session_factory", "get_async_session"]


def __getattr__(name: str):
    """Carga la UoW bajo demanda para no circular al importar modelos SQLAlchemy."""
    if name == "SQLAlchemyUnitOfWork":
        from .sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

        return SQLAlchemyUnitOfWork
    if name in {"async_session_factory", "get_async_session"}:
        from . import database

        return getattr(database, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
