"""Caso de uso para listar supermercados activos."""

from app.modules.supermarkets.application.dto.location_dto import SupermarketDTO
from app.modules.supermarkets.application.use_cases.list_supermarkets import ListSupermarketsUseCase
from app.shared.application import UnitOfWorkPort


class ListActiveSupermarketsUseCase:
    """Lista supermercados activos mediante el puerto de repositorio."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._delegate = ListSupermarketsUseCase(uow)

    async def execute(self) -> list[SupermarketDTO]:
        """Obtiene supermercados activos ordenados según la implementación del puerto."""
        return await self._delegate.execute(active_only=True)
