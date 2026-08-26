"""add auditable branch coordinate verification

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sucursal") as batch_op:
        batch_op.add_column(
            sa.Column(
                "coordenadas_verificadas",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("fuente_coordenadas", sa.String(length=2048)))
        batch_op.add_column(sa.Column("coordenadas_verificadas_en", sa.DateTime(timezone=True)))
        batch_op.create_index(
            "ix_sucursal_coordenadas_verificadas",
            ["coordenadas_verificadas"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("sucursal") as batch_op:
        batch_op.drop_index("ix_sucursal_coordenadas_verificadas")
        batch_op.drop_column("coordenadas_verificadas_en")
        batch_op.drop_column("fuente_coordenadas")
        batch_op.drop_column("coordenadas_verificadas")
