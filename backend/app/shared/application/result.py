"""Estructura genérica para resultados de casos de uso futuros."""

from dataclasses import dataclass
from typing import Generic, TypeVar


ResultValue = TypeVar("ResultValue")


@dataclass(frozen=True)
class Result(Generic[ResultValue]):
    """Transporta un valor o información de error sin decidir su presentación."""

    value: ResultValue | None = None
    error: str | None = None
