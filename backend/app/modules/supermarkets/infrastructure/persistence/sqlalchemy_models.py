"""Modelos SQLAlchemy para localización, supermercados y sucursales."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.sqlalchemy_base import Base


class ProvinceModel(Base):
    """Mapea la tabla ``provincia`` del DER."""

    __tablename__ = "provincia"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_provincia_nombre"),
        UniqueConstraint("codigo_iso", name="uq_provincia_codigo_iso"),
        Index("ix_provincia_nombre", "nombre"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_iso: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    cities: Mapped[list[CityModel]] = relationship(back_populates="province")


class CityModel(Base):
    """Mapea la tabla ``ciudad`` del DER."""

    __tablename__ = "ciudad"
    __table_args__ = (
        UniqueConstraint("provincia_id", "nombre", name="uq_ciudad_provincia_nombre"),
        CheckConstraint(
            "latitud IS NULL OR latitud BETWEEN -90 AND 90",
            name="ck_ciudad_latitud_rango",
        ),
        CheckConstraint(
            "longitud IS NULL OR longitud BETWEEN -180 AND 180",
            name="ck_ciudad_longitud_rango",
        ),
        Index("ix_ciudad_provincia_id", "provincia_id"),
        Index("ix_ciudad_nombre", "nombre"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    provincia_id: Mapped[UUID] = mapped_column(
        ForeignKey("provincia.id"),
        nullable=False,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo_postal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitud: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)

    province: Mapped[ProvinceModel] = relationship(back_populates="cities")
    branches: Mapped[list[BranchModel]] = relationship(back_populates="city")


class SupermarketModel(Base):
    """Mapea la tabla ``supermercado`` del DER."""

    __tablename__ = "supermercado"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_supermercado_nombre"),
        Index("ix_supermercado_nombre", "nombre"),
        Index("ix_supermercado_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    sitio_web: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    branches: Mapped[list[BranchModel]] = relationship(back_populates="supermarket")
    product_sources: Mapped[list["ProductSourceModel"]] = relationship(
        "ProductSourceModel",
        back_populates="supermarket",
    )


class BranchModel(Base):
    """Mapea la tabla ``sucursal`` del DER."""

    __tablename__ = "sucursal"
    __table_args__ = (
        UniqueConstraint(
            "supermercado_id",
            "nombre",
            "direccion",
            name="uq_sucursal_supermercado_nombre_direccion",
        ),
        CheckConstraint("latitud BETWEEN -90 AND 90", name="ck_sucursal_latitud_rango"),
        CheckConstraint("longitud BETWEEN -180 AND 180", name="ck_sucursal_longitud_rango"),
        Index("ix_sucursal_supermercado_id", "supermercado_id"),
        Index("ix_sucursal_ciudad_id", "ciudad_id"),
        Index("ix_sucursal_activo", "activo"),
        Index("ix_sucursal_latitud_longitud", "latitud", "longitud"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    supermercado_id: Mapped[UUID] = mapped_column(
        ForeignKey("supermercado.id"),
        nullable=False,
    )
    ciudad_id: Mapped[UUID] = mapped_column(ForeignKey("ciudad.id"), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    direccion: Mapped[str] = mapped_column(String(500), nullable=False)
    latitud: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitud: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    supermarket: Mapped[SupermarketModel] = relationship(back_populates="branches")
    city: Mapped[CityModel] = relationship(back_populates="branches")
    prices: Mapped[list["PriceModel"]] = relationship("PriceModel", back_populates="branch")
