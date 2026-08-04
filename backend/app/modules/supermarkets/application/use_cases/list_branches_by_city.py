"""Caso de uso para listar sucursales por ciudad."""

from app.modules.supermarkets.application.commands import ListBranchesByCityQuery
from app.modules.supermarkets.application.dto import BranchDTO
from app.shared.application import UnitOfWorkPort


class ListBranchesByCityUseCase:
    """Lista sucursales ubicadas en una ciudad."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: ListBranchesByCityQuery) -> list[BranchDTO]:
        """Obtiene sucursales por ciudad y devuelve DTOs."""
        async with self._uow as uow:
            branches = await uow.branches.list_by_city(query.city_id)
            return [BranchDTO.from_entity(branch) for branch in branches]
