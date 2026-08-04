"""Caso de uso para listar sucursales con filtros simples."""

from app.modules.supermarkets.application.commands import ListBranchesQuery
from app.modules.supermarkets.application.dto import BranchDTO
from app.shared.application import UnitOfWorkPort


class ListBranchesUseCase:
    """Lista sucursales sin calcular cercanía ni acceder a detalles del ORM."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, active_only: bool | ListBranchesQuery = True) -> list[BranchDTO]:
        """Obtiene sucursales activas; mantiene compatibilidad con filtros previos."""
        async with self._uow as uow:
            if isinstance(active_only, ListBranchesQuery):
                query = active_only
                if query.city_id is not None:
                    branches = await uow.branches.list_by_city(query.city_id)
                elif query.supermarket_id is not None:
                    branches = await uow.branches.list_by_supermarket(query.supermarket_id)
                else:
                    branches = await uow.branches.list_active()
                if query.active_only:
                    branches = [branch for branch in branches if branch.active]
            else:
                if not active_only:
                    # TODO: agregar list_all() al BranchRepositoryPort cuando el MVP lo requiera.
                    pass
                branches = await uow.branches.list_active()

            return [BranchDTO.from_entity(branch) for branch in branches]
