"""Internal port for semantic product search indexes."""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID


SearchMetadataValue = str | int | float | bool | None


@dataclass(frozen=True)
class ProductSearchIndexEntry:
    """Product document ready to be stored in a search index."""

    product_id: UUID
    document: str
    metadata: Mapping[str, SearchMetadataValue]


@dataclass(frozen=True)
class ProductSearchHit:
    """Search index hit normalized to the product identity."""

    product_id: UUID
    score: float


class ProductSearchIndexPort(ABC):
    """Port for product similarity search used only by catalog discovery."""

    @abstractmethod
    async def search(self, query: str, top_k: int) -> list[ProductSearchHit]:
        """Returns product ids ordered by semantic similarity."""

    @abstractmethod
    async def upsert_products(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        batch_size: int = 64,
    ) -> None:
        """Creates or updates product documents in the index."""

    @abstractmethod
    async def rebuild(
        self,
        entries: Sequence[ProductSearchIndexEntry],
        *,
        reset: bool,
        batch_size: int = 64,
    ) -> None:
        """Rebuilds the searchable product collection."""
