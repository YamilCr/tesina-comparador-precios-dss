"""Base declarativa para modelos SQLAlchemy que se crearán en los módulos."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base común de mapeos ORM; no define entidades ni tablas."""
