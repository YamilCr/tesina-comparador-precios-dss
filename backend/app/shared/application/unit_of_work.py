"""Contrato de unidad de trabajo para coordinadores de persistencia futuros."""

from abc import ABC, abstractmethod
from typing import Self


class UnitOfWork(ABC):
    """Define el ciclo transaccional sin depender de un ORM concreto."""

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Inicia el contexto transaccional."""

    @abstractmethod
    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Finaliza el contexto transaccional."""

    @abstractmethod
    async def commit(self) -> None:
        """Confirma el trabajo realizado."""

    @abstractmethod
    async def rollback(self) -> None:
        """Revierte el trabajo realizado."""
