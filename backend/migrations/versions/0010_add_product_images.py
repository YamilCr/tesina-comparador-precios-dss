"""Persist image links for canonical products and supermarket publications."""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("producto", sa.Column("image_url", sa.String(2048), nullable=True))
    op.add_column("producto_fuente", sa.Column("image_url", sa.String(2048), nullable=True))


def downgrade() -> None:
    op.drop_column("producto_fuente", "image_url")
    op.drop_column("producto", "image_url")
