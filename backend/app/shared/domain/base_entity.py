"""Abstracción mínima para entidades del dominio compartido."""

from dataclasses import dataclass
from typing import Generic, TypeVar


EntityId = TypeVar("EntityId")


@dataclass(kw_only=True)
class BaseEntity(Generic[EntityId]):
    """Define la identidad común de una entidad sin acoplarla a persistencia."""

    id: EntityId
