"""Conversores entre modelos SQLAlchemy y entidades de dominio de supermercados."""

from app.modules.supermarkets.domain.entities import Branch, City, Province, Supermarket

from .sqlalchemy_models import BranchModel, CityModel, ProvinceModel, SupermarketModel


def province_model_to_entity(model: ProvinceModel) -> Province:
    """Convierte un modelo de provincia en una entidad de dominio."""
    return Province(
        id=model.id,
        name=model.nombre,
        iso_code=model.codigo_iso,
        created_at=model.created_at,
    )


def city_model_to_entity(model: CityModel) -> City:
    """Convierte un modelo de ciudad en una entidad de dominio."""
    return City(
        id=model.id,
        province_id=model.provincia_id,
        name=model.nombre,
        postal_code=model.codigo_postal,
        latitude=model.latitud,
        longitude=model.longitud,
    )


def supermarket_model_to_entity(model: SupermarketModel) -> Supermarket:
    """Convierte un modelo de supermercado en una entidad de dominio."""
    return Supermarket(
        id=model.id,
        name=model.nombre,
        website_url=model.sitio_web,
        active=model.activo,
        created_at=model.created_at,
    )


def branch_model_to_entity(model: BranchModel) -> Branch:
    """Convierte un modelo de sucursal en una entidad de dominio."""
    return Branch(
        id=model.id,
        supermarket_id=model.supermercado_id,
        city_id=model.ciudad_id,
        name=model.nombre,
        address=model.direccion,
        latitude=model.latitud,
        longitude=model.longitud,
        active=model.activo,
    )


def province_entity_to_model(entity: Province) -> ProvinceModel:
    """Convierte una entidad de provincia en un modelo SQLAlchemy nuevo."""
    model = ProvinceModel(
        id=entity.id,
        nombre=entity.name,
        codigo_iso=entity.iso_code,
    )
    if entity.created_at is not None:
        model.created_at = entity.created_at
    return model


def city_entity_to_model(entity: City) -> CityModel:
    """Convierte una entidad de ciudad en un modelo SQLAlchemy nuevo."""
    return CityModel(
        id=entity.id,
        provincia_id=entity.province_id,
        nombre=entity.name,
        codigo_postal=entity.postal_code,
        latitud=entity.latitude,
        longitud=entity.longitude,
    )


def supermarket_entity_to_model(entity: Supermarket) -> SupermarketModel:
    """Convierte una entidad de supermercado en un modelo SQLAlchemy nuevo."""
    model = SupermarketModel(
        id=entity.id,
        nombre=entity.name,
        sitio_web=entity.website_url,
        activo=entity.active,
    )
    if entity.created_at is not None:
        model.created_at = entity.created_at
    return model


def branch_entity_to_model(entity: Branch) -> BranchModel:
    """Convierte una entidad de sucursal en un modelo SQLAlchemy nuevo."""
    return BranchModel(
        id=entity.id,
        supermercado_id=entity.supermarket_id,
        ciudad_id=entity.city_id,
        nombre=entity.name,
        direccion=entity.address,
        latitud=entity.latitude,
        longitud=entity.longitude,
        activo=entity.active,
    )
