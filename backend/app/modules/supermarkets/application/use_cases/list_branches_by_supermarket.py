"""Caso de uso para listar sucursales por supermercado."""

from app.modules.supermarkets.application.commands import ListBranchesBySupermarketQuery
from app.modules.supermarkets.application.dto import BranchDTO
from app.shared.application import UnitOfWorkPort


class ListBranchesBySupermarketUseCase:
    """Lista sucursales pertenecientes a un supermercado."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, query: ListBranchesBySupermarketQuery) -> list[BranchDTO]:
        """Obtiene sucursales por supermercado y devuelve DTOs."""
        async with self._uow as uow:
            branches = await uow.branches.list_by_supermarket(query.supermarket_id)
            return [BranchDTO.from_entity(branch) for branch in branches]
