"""ChromaDB-backed product search index."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from uuid import UUID

from app.modules.catalog.application.services import build_product_search_query
from app.modules.catalog.domain.ports import (
    ProductSearchHit,
    ProductSearchIndexEntry,
    ProductSearchIndexPort,
    SearchMetadataValue,
)


class ChromaProductSearchIndex(ProductSearchIndexPort):
    """Persistent local Chroma collection for product discovery search."""

    def __init__(
        self,
        *,
        path: Path,
        collection_name: str,
        embedding_model: str,
    ) -> None:
        self._path = path
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._client = None
        self._collection = None

    async def search(self, query: str, top_k: int) -> list[ProductSearchHit]:
        """Runs a semantic query and returns product ids with cosine-derived scores."""
        if top_k < 1:
            return []
        if not self._path.exists():
            return []
        collection = self._get_collection()
        result = collection.query(
            query_texts=[build_product_search_query(query)],
            n_results=top_k,
        )
        ids = result.get("ids", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        hits: list[ProductSearchHit] = []
        for raw_id, raw_distance in zip(ids, distances, strict=False):
            try:
                distance = float(raw_distance)
                hits.append(
                    ProductSearchHit(
                        product_id=UUID(str(raw_id)),
                        score=max(0.0, min(1.0, 1.0 - distance)),
                    )
                )
            except (TypeError, ValueError):
                continue
        return hits

    async def upsert_products(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        batch_size: int = 64,
    ) -> None:
        """Upserts product documents by product id."""
        collection = self._get_collection()
        safe_batch_size = max(1, batch_size)
        for start in range(0, len(entries), safe_batch_size):
            batch = entries[start : start + safe_batch_size]
            if not batch:
                continue
            collection.upsert(
                ids=[str(entry.product_id) for entry in batch],
                documents=[entry.document for entry in batch],
                metadatas=[_clean_metadata(entry.metadata) for entry in batch],
            )

    async def rebuild(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        reset: bool,
        batch_size: int = 64,
    ) -> None:
        """Optionally resets and then upserts all product documents."""
        if reset:
            client = self._get_client()
            try:
                client.delete_collection(self._collection_name)
            except Exception:
                pass
            self._collection = None
        await self.upsert_products(entries, batch_size=batch_size)

    def _get_client(self):
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self._path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    chroma_product_telemetry_impl=(
                        "app.modules.catalog.infrastructure.search.noop_telemetry."
                        "NoopProductTelemetry"
                    ),
                    chroma_telemetry_impl=(
                        "app.modules.catalog.infrastructure.search.noop_telemetry."
                        "NoopProductTelemetry"
                    ),
                ),
            )
        return self._client

    def _get_collection(self):
        if self._collection is None:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

            embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=self._embedding_model,
            )
            self._collection = self._get_client().get_or_create_collection(
                name=self._collection_name,
                embedding_function=embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection


def _clean_metadata(
    metadata: Mapping[str, SearchMetadataValue],
) -> dict[str, str | int | float | bool]:
    return {
        str(key): value
        for key, value in metadata.items()
        if value is not None and _is_chroma_metadata_value(value)
    }


def _is_chroma_metadata_value(value: SearchMetadataValue) -> bool:
    return isinstance(value, str | int | float | bool)
