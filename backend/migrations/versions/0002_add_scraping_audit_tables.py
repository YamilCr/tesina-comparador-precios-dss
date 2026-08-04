"""add scraping audit tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scraping_source",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("supermercado_id", sa.Uuid(), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supermercado_id"], ["supermercado.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supermercado_id",
            "nombre",
            name="uq_scraping_source_supermercado_nombre",
        ),
    )
    op.create_index("ix_scraping_source_activo", "scraping_source", ["activo"], unique=False)
    op.create_index("ix_scraping_source_nombre", "scraping_source", ["nombre"], unique=False)
    op.create_index(
        "ix_scraping_source_supermercado_id",
        "scraping_source",
        ["supermercado_id"],
        unique=False,
    )

    op.create_table(
        "scraping_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scraping_source_id", sa.Uuid(), nullable=False),
        sa.Column("estado", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("iniciado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items_extraidos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("items_cargados", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mensaje_error", sa.String(length=2000), nullable=True),
        sa.CheckConstraint(
            "estado IN ('pending', 'running', 'succeeded', 'failed')",
            name="ck_scraping_run_estado_valido",
        ),
        sa.CheckConstraint(
            "finalizado_en IS NULL OR finalizado_en >= iniciado_en",
            name="ck_scraping_run_finalizado_despues_inicio",
        ),
        sa.CheckConstraint(
            "items_cargados >= 0",
            name="ck_scraping_run_items_cargados_no_negativo",
        ),
        sa.CheckConstraint(
            "items_extraidos >= 0",
            name="ck_scraping_run_items_extraidos_no_negativo",
        ),
        sa.ForeignKeyConstraint(["scraping_source_id"], ["scraping_source.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scraping_run_estado", "scraping_run", ["estado"], unique=False)
    op.create_index("ix_scraping_run_iniciado_en", "scraping_run", ["iniciado_en"], unique=False)
    op.create_index(
        "ix_scraping_run_source_id",
        "scraping_run",
        ["scraping_source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scraping_run_source_id", table_name="scraping_run")
    op.drop_index("ix_scraping_run_iniciado_en", table_name="scraping_run")
    op.drop_index("ix_scraping_run_estado", table_name="scraping_run")
    op.drop_table("scraping_run")
    op.drop_index("ix_scraping_source_supermercado_id", table_name="scraping_source")
    op.drop_index("ix_scraping_source_nombre", table_name="scraping_source")
    op.drop_index("ix_scraping_source_activo", table_name="scraping_source")
    op.drop_table("scraping_source")
