"""Store semantic product-search vectors in PostgreSQL with pgvector."""

from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE product_search_vector (
            product_id UUID PRIMARY KEY REFERENCES producto(id) ON DELETE CASCADE,
            document TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            embedding vector(384) NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_product_search_vector_embedding_cosine
        ON product_search_vector USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TABLE IF EXISTS product_search_vector")
