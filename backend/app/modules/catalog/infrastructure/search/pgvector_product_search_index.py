"""PostgreSQL/pgvector implementation of the semantic product search index."""

import asyncio
import json
from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.catalog.application.services import build_product_search_query
from app.modules.catalog.domain.ports import (
    ProductSearchHit,
    ProductSearchIndexEntry,
    ProductSearchIndexPort,
)


class PgVectorProductSearchIndex(ProductSearchIndexPort):
    """Stores product embeddings in the shared PostgreSQL database.

    The table is created by Alembic migration 0011.  Keeping vectors in
    PostgreSQL lets the API and scheduled scraping job read the same index.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        embedding_model: str,
        embedding_dimensions: int,
    ) -> None:
        self._session_factory = session_factory
        self._embedding_model = embedding_model
        self._embedding_dimensions = embedding_dimensions

    async def search(self, query: str, top_k: int) -> list[ProductSearchHit]:
        if top_k < 1 or not query.strip():
            return []
        embedding = await self._embed(build_product_search_query(query))
        async with self._session_factory() as session:
            self._require_postgres(session)
            rows = await session.execute(
                text(
                    """
                    SELECT product_id, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                    FROM product_search_vector
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT :top_k
                    """
                ),
                {"embedding": _vector_literal(embedding), "top_k": top_k},
            )
            records = rows.all()
        return [
            ProductSearchHit(product_id=UUID(str(row.product_id)), score=float(row.score))
            for row in records
            if row.product_id is not None and row.score is not None
        ]

    async def upsert_products(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        batch_size: int = 64,
    ) -> None:
        if not entries:
            return
        safe_batch_size = max(1, batch_size)
        for start in range(0, len(entries), safe_batch_size):
            batch = entries[start : start + safe_batch_size]
            embeddings = await asyncio.gather(*(self._embed(entry.document) for entry in batch))
            async with self._session_factory() as session:
                self._require_postgres(session)
                for entry, embedding in zip(batch, embeddings, strict=True):
                    await session.execute(
                        text(
                            """
                            INSERT INTO product_search_vector
                                (product_id, document, metadata, embedding, updated_at)
                            VALUES
                                (:product_id, :document, CAST(:metadata AS jsonb),
                                 CAST(:embedding AS vector), CURRENT_TIMESTAMP)
                            ON CONFLICT (product_id) DO UPDATE SET
                                document = EXCLUDED.document,
                                metadata = EXCLUDED.metadata,
                                embedding = EXCLUDED.embedding,
                                updated_at = CURRENT_TIMESTAMP
                            """
                        ),
                        {
                            "product_id": str(entry.product_id),
                            "document": entry.document,
                            "metadata": json.dumps(entry.metadata),
                            "embedding": _vector_literal(embedding),
                        },
                    )
                await session.commit()

    async def rebuild(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        reset: bool,
        batch_size: int = 64,
    ) -> None:
        if reset:
            async with self._session_factory() as session:
                self._require_postgres(session)
                await session.execute(text("DELETE FROM product_search_vector"))
                await session.commit()
        await self.upsert_products(entries, batch_size=batch_size)

    async def _embed(self, document: str) -> list[float]:
        vector = await asyncio.to_thread(
            _embedding_model(self._embedding_model).encode,
            document,
            normalize_embeddings=True,
        )
        values = [float(value) for value in vector]
        if len(values) != self._embedding_dimensions:
            raise ValueError(
                "Embedding dimension does not match VECTOR_EMBEDDING_DIMENSIONS "
                f"({len(values)} != {self._embedding_dimensions})."
            )
        return values

    @staticmethod
    def _require_postgres(session: AsyncSession) -> None:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            raise RuntimeError("pgvector requires a PostgreSQL DATABASE_URL.")


@lru_cache(maxsize=2)
def _embedding_model(model_name: str):
    """Lazily loads and reuses the embedding model in each process."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"
