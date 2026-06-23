"""Adaptador SQLAlchemy asíncrono para el puerto de sucursales."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.supermarkets.domain.entities import Branch
from app.modules.supermarkets.domain.ports import BranchRepositoryPort

from .mappers import branch_entity_to_model, branch_model_to_entity
from .sqlalchemy_models import BranchModel


class SQLAlchemyBranchRepository(BranchRepositoryPort):
    """Implementa el acceso a sucursales sin incorporar cálculos de distancia."""

    def __init__(self, session: AsyncSession) -> None:
        """Recibe una sesión cuyo ciclo de vida pertenece a la capa llamadora."""
        self._session = session

    async def get_by_id(self, branch_id: UUID) -> Branch | None:
        """Obtiene una sucursal por identificador."""
        model = await self._session.get(BranchModel, branch_id)
        return branch_model_to_entity(model) if model is not None else None

    async def list_active(self) -> list[Branch]:
        """Lista las sucursales activas ordenadas por nombre."""
        models = await self._session.scalars(
            select(BranchModel).where(BranchModel.activo.is_(True)).order_by(BranchModel.nombre)
        )
        return [branch_model_to_entity(model) for model in models.all()]

    async def list_by_supermarket(self, supermarket_id: UUID) -> list[Branch]:
        """Lista las sucursales de un supermercado ordenadas por nombre."""
        models = await self._session.scalars(
            select(BranchModel)
            .where(BranchModel.supermercado_id == supermarket_id)
            .order_by(BranchModel.nombre)
        )
        return [branch_model_to_entity(model) for model in models.all()]

    async def list_by_city(self, city_id: UUID) -> list[Branch]:
        """Lista las sucursales de una ciudad ordenadas por nombre."""
        models = await self._session.scalars(
            select(BranchModel).where(BranchModel.ciudad_id == city_id).order_by(BranchModel.nombre)
        )
        return [branch_model_to_entity(model) for model in models.all()]

    async def save(self, branch: Branch) -> Branch:
        """Crea o actualiza una sucursal sin confirmar la transacción."""
        model = await self._session.get(BranchModel, branch.id)
        if model is None:
            model = branch_entity_to_model(branch)
            self._session.add(model)
        else:
            model.supermercado_id = branch.supermarket_id
            model.ciudad_id = branch.city_id
            model.nombre = branch.name
            model.direccion = branch.address
            model.latitud = branch.latitude
            model.longitud = branch.longitude
            model.activo = branch.active

        await self._session.flush()
        return branch_model_to_entity(model)
