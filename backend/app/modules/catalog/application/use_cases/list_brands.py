"""Caso de uso para listar marcas del catálogo."""

from app.modules.catalog.application.dto import BrandDTO
from app.shared.application import UnitOfWorkPort


class ListBrandsUseCase:
    """Lista marcas del catálogo mediante UnitOfWorkPort."""

    def __init__(self, uow: UnitOfWorkPort) -> None:
        """Recibe el Unit of Work de aplicación."""
        self._uow = uow

    async def execute(self, active_only: bool = True) -> list[BrandDTO]:
        """Lista marcas activas o todas las marcas según el parámetro."""
        async with self._uow as uow:
            brands = (
                await uow.brands.list_active()
                if active_only
                else await uow.brands.list_all()
            )
            return [BrandDTO.from_entity(brand) for brand in brands]
