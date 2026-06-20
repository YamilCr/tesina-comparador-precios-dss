"""Abstracciones para objetos de valor inmutables del dominio."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Marca base para valores del dominio definidos por sus atributos."""
