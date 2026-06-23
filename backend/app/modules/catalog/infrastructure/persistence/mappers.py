"""Conversores entre modelos SQLAlchemy y entidades de dominio del catálogo."""

from app.modules.catalog.domain.entities import Brand, Product, ProductCategory, ProductSource

from .sqlalchemy_models import BrandModel, ProductCategoryModel, ProductModel, ProductSourceModel


def product_category_model_to_entity(model: ProductCategoryModel) -> ProductCategory:
    """Convierte un modelo de categoría en una entidad de dominio."""
    return ProductCategory(
        id=model.id,
        name=model.nombre,
        description=model.descripcion,
        parent_category_id=model.categoria_padre_id,
        active=model.activo,
    )


def brand_model_to_entity(model: BrandModel) -> Brand:
    """Convierte un modelo de marca en una entidad de dominio."""
    return Brand(
        id=model.id,
        name=model.nombre,
        description=model.descripcion,
        active=model.activo,
    )


def product_model_to_entity(model: ProductModel) -> Product:
    """Convierte un modelo de producto en una entidad de dominio."""
    return Product(
        id=model.id,
        category_id=model.categoria_id,
        brand_id=model.marca_id,
        normalized_name=model.nombre_normalizado,
        description=model.descripcion,
        unit_measure=model.unidad_medida,
        net_content=model.contenido_neto,
        internal_code=model.codigo_interno,
        active=model.activo,
    )


def product_source_model_to_entity(model: ProductSourceModel) -> ProductSource:
    """Convierte un modelo de producto fuente en una entidad de dominio."""
    return ProductSource(
        id=model.id,
        product_id=model.producto_id,
        supermarket_id=model.supermercado_id,
        original_name=model.nombre_original,
        external_code=model.codigo_externo,
        product_url=model.url_producto,
        original_unit=model.unidad_original,
        match_confidence=model.confianza_match,
        active=model.activo,
    )


def product_category_entity_to_model(entity: ProductCategory) -> ProductCategoryModel:
    """Convierte una entidad de categoría en un modelo SQLAlchemy nuevo."""
    return ProductCategoryModel(
        id=entity.id,
        nombre=entity.name,
        descripcion=entity.description,
        categoria_padre_id=entity.parent_category_id,
        activo=entity.active,
    )


def brand_entity_to_model(entity: Brand) -> BrandModel:
    """Convierte una entidad de marca en un modelo SQLAlchemy nuevo."""
    return BrandModel(
        id=entity.id,
        nombre=entity.name,
        descripcion=entity.description,
        activo=entity.active,
    )


def product_entity_to_model(entity: Product) -> ProductModel:
    """Convierte una entidad de producto en un modelo SQLAlchemy nuevo."""
    return ProductModel(
        id=entity.id,
        categoria_id=entity.category_id,
        marca_id=entity.brand_id,
        nombre_normalizado=entity.normalized_name,
        descripcion=entity.description,
        unidad_medida=entity.unit_measure,
        contenido_neto=entity.net_content,
        codigo_interno=entity.internal_code,
        activo=entity.active,
    )


def product_source_entity_to_model(entity: ProductSource) -> ProductSourceModel:
    """Convierte una entidad de producto fuente en un modelo SQLAlchemy nuevo."""
    return ProductSourceModel(
        id=entity.id,
        producto_id=entity.product_id,
        supermercado_id=entity.supermarket_id,
        nombre_original=entity.original_name,
        codigo_externo=entity.external_code,
        url_producto=entity.product_url,
        unidad_original=entity.original_unit,
        confianza_match=entity.match_confidence,
        activo=entity.active,
    )
