"""Modelos SQLAlchemy para auditoria de scraping e ingesta."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.sqlalchemy_base import Base

if TYPE_CHECKING:
    from app.modules.supermarkets.infrastructure.persistence import SupermarketModel


class ScrapingSourceModel(Base):
    """Mapea la tabla ``scraping_source``."""

    __tablename__ = "scraping_source"
    __table_args__ = (
        UniqueConstraint(
            "supermercado_id",
            "nombre",
            name="uq_scraping_source_supermercado_nombre",
        ),
        Index("ix_scraping_source_supermercado_id", "supermercado_id"),
        Index("ix_scraping_source_sucursal_id", "sucursal_id"),
        Index("ix_scraping_source_nombre", "nombre"),
        Index("ix_scraping_source_activo", "activo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    supermercado_id: Mapped[UUID] = mapped_column(
        ForeignKey("supermercado.id"),
        nullable=False,
    )
    sucursal_id: Mapped[UUID | None] = mapped_column(ForeignKey("sucursal.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    scraper_key: Mapped[str] = mapped_column(String(32), nullable=False, default="jumbo")
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

    supermarket: Mapped["SupermarketModel"] = relationship(
        "SupermarketModel",
        back_populates="scraping_sources",
    )
    runs: Mapped[list["ScrapingRunModel"]] = relationship(back_populates="source")
    schedule: Mapped["ScrapingScheduleModel | None"] = relationship(
        back_populates="source",
        uselist=False,
    )


class ScrapingRunModel(Base):
    """Mapea la tabla ``scraping_run``."""

    __tablename__ = "scraping_run"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_scraping_run_estado_valido",
        ),
        CheckConstraint(
            "items_extraidos >= 0",
            name="ck_scraping_run_items_extraidos_no_negativo",
        ),
        CheckConstraint(
            "items_cargados >= 0",
            name="ck_scraping_run_items_cargados_no_negativo",
        ),
        CheckConstraint(
            "finalizado_en IS NULL OR finalizado_en >= iniciado_en",
            name="ck_scraping_run_finalizado_despues_inicio",
        ),
        Index("ix_scraping_run_source_id", "scraping_source_id"),
        Index("ix_scraping_run_estado", "estado"),
        Index("ix_scraping_run_iniciado_en", "iniciado_en"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    scraping_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("scraping_source.id"),
        nullable=False,
    )
    estado: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    items_extraidos: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    items_cargados: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    mensaje_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    source: Mapped[ScrapingSourceModel] = relationship(back_populates="runs")
    scraped_products: Mapped[list["ScrapedProductModel"]] = relationship(back_populates="run")
    schedule_execution: Mapped["ScheduledRefreshExecutionModel | None"] = relationship(
        back_populates="scraping_run",
        uselist=False,
    )


class ScrapingScheduleModel(Base):
    """Stores one configurable automatic refresh plan per scraping source."""

    __tablename__ = "scraping_schedule"
    __table_args__ = (
        UniqueConstraint("scraping_source_id", name="uq_scraping_schedule_source"),
        CheckConstraint(
            "interval_minutes BETWEEN 1 AND 10080",
            name="ck_scraping_schedule_interval",
        ),
        CheckConstraint(
            "retry_delay_minutes BETWEEN 1 AND 1440",
            name="ck_scraping_schedule_retry_delay",
        ),
        CheckConstraint(
            "result_limit BETWEEN 1 AND 20",
            name="ck_scraping_schedule_result_limit",
        ),
        CheckConstraint(
            "timeout_seconds BETWEEN 1 AND 300",
            name="ck_scraping_schedule_timeout",
        ),
        CheckConstraint(
            "consecutive_failures >= 0",
            name="ck_scraping_schedule_failures_nonnegative",
        ),
        Index("ix_scraping_schedule_enabled_next_run", "enabled", "next_run_at"),
        Index("ix_scraping_schedule_locked_until", "locked_until"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    scraping_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("scraping_source.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    queries: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    result_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    source: Mapped[ScrapingSourceModel] = relationship(back_populates="schedule")
    executions: Mapped[list["ScheduledRefreshExecutionModel"]] = relationship(
        back_populates="schedule"
    )


class ScheduledRefreshExecutionModel(Base):
    """Stores scheduler-level history and links it to source run auditing."""

    __tablename__ = "scheduled_refresh_execution"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')",
            name="ck_scheduled_refresh_execution_status",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_scheduled_refresh_execution_finished_after_start",
        ),
        UniqueConstraint("scraping_run_id", name="uq_scheduled_refresh_execution_run"),
        Index("ix_scheduled_refresh_execution_schedule", "schedule_id"),
        Index("ix_scheduled_refresh_execution_status", "status"),
        Index("ix_scheduled_refresh_execution_started_at", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    schedule_id: Mapped[UUID] = mapped_column(
        ForeignKey("scraping_schedule.id"),
        nullable=False,
    )
    scraping_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("scraping_run.id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="running",
        server_default="running",
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    schedule: Mapped[ScrapingScheduleModel] = relationship(back_populates="executions")
    scraping_run: Mapped[ScrapingRunModel | None] = relationship(
        back_populates="schedule_execution"
    )


class ScrapedProductModel(Base):
    """Maps raw extracted items and their ETL quality outcome."""

    __tablename__ = "producto_extraido"
    __table_args__ = (
        CheckConstraint(
            "estado IN ('pending', 'loaded', 'rejected', 'duplicate', 'unmatched')",
            name="ck_producto_extraido_estado_valido",
        ),
        Index("ix_producto_extraido_run_id", "scraping_run_id"),
        Index("ix_producto_extraido_estado", "estado"),
        Index("ix_producto_extraido_codigo_externo", "codigo_externo"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    scraping_run_id: Mapped[UUID] = mapped_column(ForeignKey("scraping_run.id"), nullable=False)
    codigo_externo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nombre: Mapped[str | None] = mapped_column(String(500), nullable=True)
    marca: Mapped[str | None] = mapped_column(String(255), nullable=True)
    precio: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    presentacion: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url_producto: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    payload_crudo: Mapped[dict] = mapped_column(JSON, nullable=False)
    estado: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    mensaje_calidad: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    producto_fuente_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("producto_fuente.id"), nullable=True
    )
    precio_id: Mapped[UUID | None] = mapped_column(ForeignKey("precio.id"), nullable=True)
    procesado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    run: Mapped[ScrapingRunModel] = relationship(back_populates="scraped_products")


class ProductIdentityReviewModel(Base):
    """Stores a pending or decided human review of one canonical merge."""

    __tablename__ = "revision_identidad_producto"
    __table_args__ = (
        UniqueConstraint(
            "tipo",
            "producto_origen_id",
            "producto_destino_id",
            "valor_evidencia",
            name="uq_revision_identidad_propuesta",
        ),
        CheckConstraint(
            "tipo IN ('gtin_conflict', 'semantic_alias')",
            name="ck_revision_identidad_tipo",
        ),
        CheckConstraint(
            "estado IN ('pending', 'approved', 'rejected')",
            name="ck_revision_identidad_estado",
        ),
        CheckConstraint(
            "confianza BETWEEN 0 AND 1",
            name="ck_revision_identidad_confianza",
        ),
        Index("ix_revision_identidad_estado", "estado"),
        Index("ix_revision_identidad_origen", "producto_origen_id"),
        Index("ix_revision_identidad_destino", "producto_destino_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(32), nullable=False)
    producto_origen_id: Mapped[UUID] = mapped_column(
        ForeignKey("producto.id"), nullable=False
    )
    producto_destino_id: Mapped[UUID] = mapped_column(
        ForeignKey("producto.id"), nullable=False
    )
    valor_evidencia: Mapped[str] = mapped_column(String(500), nullable=False)
    confianza: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    justificacion: Mapped[str] = mapped_column(String(1000), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", server_default="pending"
    )
    nota_decision: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
