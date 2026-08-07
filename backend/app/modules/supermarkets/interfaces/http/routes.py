"""Rutas HTTP de supermercados, ciudades y sucursales."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_unit_of_work
from app.modules.supermarkets.application.dto import ListBranchesQuery
from app.modules.supermarkets.application.use_cases import (
    ListActiveSupermarketsUseCase,
    ListBranchesUseCase,
    ListCitiesUseCase,
)
from app.shared.application import UnitOfWorkPort
from app.shared.interfaces.http import collection_response, paginated_response

from .schemas import BranchResponse, CityResponse, SupermarketResponse


router = APIRouter(tags=["supermarkets"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


async def _branch_display_names(
    uow: UnitOfWorkPort,
    branches,
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Carga nombres de supermercados y ciudades para respuestas HTTP."""
    supermarket_ids = {branch.supermarket_id for branch in branches}
    city_ids = {branch.city_id for branch in branches}
    supermarket_names: dict[UUID, str] = {}
    city_names: dict[UUID, str] = {}

    if not supermarket_ids and not city_ids:
        return supermarket_names, city_names

    async with uow as read_uow:
        for current_supermarket_id in supermarket_ids:
            supermarket = await read_uow.supermarkets.get_by_id(current_supermarket_id)
            if supermarket is not None:
                supermarket_names[supermarket.id] = supermarket.name
        for current_city_id in city_ids:
            city = await read_uow.cities.get_by_id(current_city_id)
            if city is not None:
                city_names[city.id] = city.name
    return supermarket_names, city_names


async def _city_province_names(uow: UnitOfWorkPort, cities) -> dict[UUID, str]:
    """Loads province names for serialized cities."""
    province_ids = {city.province_id for city in cities}
    province_names: dict[UUID, str] = {}

    if not province_ids:
        return province_names

    async with uow as read_uow:
        for province_id in province_ids:
            province = await read_uow.provinces.get_by_id(province_id)
            if province is not None:
                province_names[province.id] = province.name
    return province_names


@router.get("/locations/cities")
async def list_cities(uow: UnitOfWorkDependency) -> dict:
    """Lista ciudades disponibles para consultas de ubicación."""
    cities = await ListCitiesUseCase(uow).execute()
    province_names = await _city_province_names(uow, cities)
    return collection_response(
        [
            CityResponse(
                id=city.id,
                province_id=city.province_id,
                province_name=province_names.get(city.province_id),
                name=city.name,
                postal_code=city.postal_code,
                latitude=city.latitude,
                longitude=city.longitude,
            ).model_dump(mode="json")
            for city in cities
        ]
    )


@router.get("/supermarkets")
async def list_supermarkets(uow: UnitOfWorkDependency) -> dict:
    """Lista supermercados activos."""
    supermarkets = await ListActiveSupermarketsUseCase(uow).execute()
    return collection_response(
        [
            SupermarketResponse(
                id=supermarket.id,
                name=supermarket.name,
                website_url=supermarket.website_url,
            ).model_dump(mode="json")
            for supermarket in supermarkets
        ]
    )


@router.get("/branches")
async def list_branches(
    uow: UnitOfWorkDependency,
    city_id: UUID | None = None,
    supermarket_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Lista sucursales activas con filtros opcionales."""
    branches = await ListBranchesUseCase(uow).execute(
        ListBranchesQuery(city_id=city_id, supermarket_id=supermarket_id)
    )
    start = (page - 1) * page_size
    end = start + page_size
    paginated_branches = branches[start:end]
    supermarket_names, city_names = await _branch_display_names(uow, paginated_branches)
    items = [
            BranchResponse(
                id=branch.id,
                supermarket_id=branch.supermarket_id,
                supermarket_name=supermarket_names.get(branch.supermarket_id),
                city_id=branch.city_id,
                city_name=city_names.get(branch.city_id),
                name=branch.name,
                address=branch.address,
                latitude=branch.latitude,
                longitude=branch.longitude,
            ).model_dump(mode="json")
            for branch in paginated_branches
    ]
    return paginated_response(
        items,
        page=page,
        page_size=page_size,
        total=len(branches),
    )
