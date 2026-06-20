"""DTOs de paginación reutilizables para casos de uso futuros."""

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar


Item = TypeVar("Item")


@dataclass(frozen=True)
class PageRequest:
    """Describe la página solicitada sin imponer reglas de consulta."""

    number: int = 1
    size: int = 20


@dataclass(frozen=True)
class Page(Generic[Item]):
    """Representa una respuesta paginada independiente del transporte HTTP."""

    items: Sequence[Item]
    total: int
    request: PageRequest
