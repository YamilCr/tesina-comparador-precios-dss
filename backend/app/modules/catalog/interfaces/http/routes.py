"""Rutas HTTP del catálogo conectadas con casos de uso de aplicación."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_unit_of_work
from app.modules.catalog.application.commands import ProductListQuery, ProductSearchQuery
from app.modules.catalog.application.use_cases import (
    ListActiveCategoriesUseCase,
    ListActiveProductsUseCase,
    ListBrandsUseCase,
    SearchProductsUseCase,
)
from app.shared.application import UnitOfWorkPort
from app.shared.interfaces.http import collection_response, paginated_response

from .schemas import BrandResponse, ProductCategoryResponse, ProductResponse


router = APIRouter(prefix="/catalog", tags=["catalog"])
UnitOfWorkDependency = Annotated[UnitOfWorkPort, Depends(get_unit_of_work)]


async def _product_display_names(
    uow: UnitOfWorkPort,
    products,
) -> tuple[dict[UUID, str], dict[UUID, str]]:
    """Carga nombres de categorias y marcas para respuestas HTTP."""
    category_ids = {product.category_id for product in products if product.category_id is not None}
    brand_ids = {product.brand_id for product in products if product.brand_id is not None}
    category_names: dict[UUID, str] = {}
    brand_names: dict[UUID, str] = {}

    if not category_ids and not brand_ids:
        return category_names, brand_names

    async with uow as read_uow:
        for category_id in category_ids:
            category = await read_uow.product_categories.get_by_id(category_id)
            if category is not None:
                category_names[category.id] = category.name
        for brand_id in brand_ids:
            brand = await read_uow.brands.get_by_id(brand_id)
            if brand is not None:
                brand_names[brand.id] = brand.name
    return category_names, brand_names


@router.get("/products")
async def list_products(
    uow: UnitOfWorkDependency,
    q: str | None = Query(default=None, max_length=120),
    category_id: UUID | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Busca o lista productos activos del catálogo."""
    if q and q.strip():
        products = await SearchProductsUseCase(uow).execute(
            ProductSearchQuery(query=q, limit=page_size)
        )
    else:
        products = await ListActiveProductsUseCase(uow).execute(
            ProductListQuery(limit=page_size, offset=(page - 1) * page_size)
        )

    if category_id is not None:
        products = [product for product in products if product.category_id == category_id]

    category_names, brand_names = await _product_display_names(uow, products)

    items = [
            ProductResponse(
                id=product.id,
                normalized_name=product.normalized_name,
                category_id=product.category_id,
                category_name=(
                    category_names.get(product.category_id)
                    if product.category_id is not None
                    else None
                ),
                brand_id=product.brand_id,
                brand_name=brand_names.get(product.brand_id) if product.brand_id is not None else None,
                description=product.description,
                unit_measure=product.unit_measure,
                net_content=product.net_content,
                internal_code=product.internal_code,
            ).model_dump(mode="json")
            for product in products
    ]
    return paginated_response(
        items,
        page=page,
        page_size=page_size,
        total=len(products),
    )


@router.get("/categories")
async def list_categories(uow: UnitOfWorkDependency) -> dict:
    """Lista categorías activas del catálogo."""
    categories = await ListActiveCategoriesUseCase(uow).execute()
    return collection_response(
        [
            ProductCategoryResponse(
                id=category.id,
                name=category.name,
                description=category.description,
                parent_category_id=category.parent_category_id,
            ).model_dump(mode="json")
            for category in categories
        ]
    )


@router.get("/brands")
async def list_brands(
    uow: UnitOfWorkDependency,
    active_only: bool = Query(default=True),
) -> dict:
    """Lista marcas del catálogo."""
    brands = await ListBrandsUseCase(uow).execute(active_only=active_only)
    return collection_response(
        [
            BrandResponse(
                id=brand.id,
                name=brand.name,
                description=brand.description,
            ).model_dump(mode="json")
            for brand in brands
        ]
    )
