"""Caso de uso para listar supermercados."""

from app.modules.supermarkets.application.dto import SupermarketDTO
from app.shared.application import UnitOfWorkPort


class ListSupermarketsUseCase:
    """Lista supermercados mediante UnitOfWorkPort."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, active_only: bool = True) -> list[SupermarketDTO]:
        """Lista supermercados activos o todos los supermercados."""
        async with self._uow as uow:
            supermarkets = (
                await uow.supermarkets.list_active()
                if active_only
                else await uow.supermarkets.list_all()
            )
            return [SupermarketDTO.from_entity(supermarket) for supermarket in supermarkets]
