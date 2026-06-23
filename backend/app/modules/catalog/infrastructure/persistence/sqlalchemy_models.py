"""Modelos SQLAlchemy para el catálogo normalizado y sus fuentes externas."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.sqlalchemy_base import Base


class ProductCategoryModel(Base):
    """Mapea la tabla ``categoria_producto`` del DER."""

    __tablename__ = "categoria_producto"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_categoria_producto_nombre"),
        Index("ix_categoria_producto_nombre", "nombre"),
        Index("ix_categoria_producto_activo", "activo"),
        Index("ix_categoria_producto_padre_id", "categoria_padre_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    categoria_padre_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categoria_producto.id"),
        nullable=True,
    )
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    parent: Mapped[ProductCategoryModel | None] = relationship(
        back_populates="children",
        remote_side="ProductCategoryModel.id",
    )
    children: Mapped[list[ProductCategoryModel]] = relationship(back_populates="parent")
    products: Mapped[list[ProductModel]] = relationship(back_populates="category")


class BrandModel(Base):
    """Mapea la tabla ``marca`` del DER."""

    __tablename__ = "marca"
    __table_args__ = (
        UniqueConstraint("nombre", name="uq_marca_nombre"),
        Index("ix_marca_nombre", "nombre"),
        Index("ix_marca_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    products: Mapped[list[ProductModel]] = relationship(back_populates="brand")


class ProductModel(Base):
    """Mapea la tabla ``producto`` del DER."""

    __tablename__ = "producto"
    __table_args__ = (
        UniqueConstraint("codigo_interno", name="uq_producto_codigo_interno"),
        CheckConstraint(
            "contenido_neto IS NULL OR contenido_neto > 0",
            name="ck_producto_contenido_neto_positivo",
        ),
        Index("ix_producto_nombre_normalizado", "nombre_normalizado"),
        Index("ix_producto_categoria_id", "categoria_id"),
        Index("ix_producto_marca_id", "marca_id"),
        Index("ix_producto_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    categoria_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("categoria_producto.id"),
        nullable=True,
    )
    marca_id: Mapped[UUID | None] = mapped_column(ForeignKey("marca.id"), nullable=True)
    nombre_normalizado: Mapped[str] = mapped_column(String(500), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    unidad_medida: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contenido_neto: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    codigo_interno: Mapped[str | None] = mapped_column(String(128), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    category: Mapped[ProductCategoryModel | None] = relationship(back_populates="products")
    brand: Mapped[BrandModel | None] = relationship(back_populates="products")
    product_sources: Mapped[list[ProductSourceModel]] = relationship(back_populates="product")


class ProductSourceModel(Base):
    """Mapea la tabla ``producto_fuente`` del DER."""

    __tablename__ = "producto_fuente"
    __table_args__ = (
        UniqueConstraint(
            "supermercado_id",
            "codigo_externo",
            name="uq_producto_fuente_supermercado_codigo_externo",
        ),
        CheckConstraint(
            "confianza_match IS NULL OR confianza_match BETWEEN 0 AND 1",
            name="ck_producto_fuente_confianza_match_rango",
        ),
        Index("ix_producto_fuente_producto_id", "producto_id"),
        Index("ix_producto_fuente_supermercado_id", "supermercado_id"),
        Index("ix_producto_fuente_nombre_original", "nombre_original"),
        Index("ix_producto_fuente_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    producto_id: Mapped[UUID] = mapped_column(ForeignKey("producto.id"), nullable=False)
    supermercado_id: Mapped[UUID] = mapped_column(
        ForeignKey("supermercado.id"),
        nullable=False,
    )
    nombre_original: Mapped[str] = mapped_column(String(500), nullable=False)
    codigo_externo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_producto: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    unidad_original: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confianza_match: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    activo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    product: Mapped[ProductModel] = relationship(back_populates="product_sources")
    supermarket: Mapped["SupermarketModel"] = relationship(
        "SupermarketModel",
        back_populates="product_sources",
    )
    prices: Mapped[list["PriceModel"]] = relationship("PriceModel", back_populates="product_source")
