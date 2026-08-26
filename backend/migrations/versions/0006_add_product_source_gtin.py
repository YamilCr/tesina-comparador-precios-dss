"""add canonical product GTIN support

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("producto_fuente") as batch_op:
        batch_op.add_column(sa.Column("gtin", sa.String(length=14), nullable=True))
        batch_op.create_index("ix_producto_fuente_gtin", ["gtin"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("producto_fuente") as batch_op:
        batch_op.drop_index("ix_producto_fuente_gtin")
        batch_op.drop_column("gtin")
