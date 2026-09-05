"""Rebuilds the local product semantic search index from active catalog products."""

import argparse
import asyncio

from app.config import get_settings
from app.dependencies import get_product_search_index
from app.modules.catalog.application.services import build_product_search_entry
from app.modules.catalog.domain.ports import ProductSearchIndexPort
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reindex active products into the local Chroma search collection."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the configured Chroma collection before indexing.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Number of product documents to upsert per batch.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be greater than zero.")

    settings = get_settings()
    search_index = get_product_search_index()
    if search_index is None:
        raise SystemExit("Vector search is disabled. Set VECTOR_SEARCH_ENABLED=true.")

    entries = await _load_index_entries()
    await _rebuild(search_index, entries, reset=args.reset, batch_size=args.batch_size)
    print(
        "Indexed "
        f"{len(entries)} active products into {settings.vector_collection} "
        f"at {settings.vector_store_path}"
    )


async def _load_index_entries():
    async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
        products = await uow.products.list_active(limit=100_000)
        brands = await uow.brands.list_active()
        categories = await uow.product_categories.list_active()
        brand_names = {brand.id: brand.name for brand in brands}
        category_names = {category.id: category.name for category in categories}
        return [
            build_product_search_entry(
                product,
                brand_name=brand_names.get(product.brand_id),
                category_name=category_names.get(product.category_id),
            )
            for product in products
        ]


async def _rebuild(
    search_index: ProductSearchIndexPort,
    entries,
    *,
    reset: bool,
    batch_size: int,
) -> None:
    await search_index.rebuild(entries, reset=reset, batch_size=batch_size)


if __name__ == "__main__":
    asyncio.run(main())
