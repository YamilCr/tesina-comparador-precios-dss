"""Fill missing categories only from consistent explicit source evidence."""

import argparse
import asyncio
from collections import defaultdict
from uuid import uuid4

from app.modules.catalog.domain.entities import ProductCategory
from app.modules.ingestion.application.category_evidence import category_from_payload
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


async def main(apply: bool) -> None:
    async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
        sources = {source.id: source for source in await uow.product_sources.list_all() if source.active}
        evidence = defaultdict(dict)
        for staged in await uow.ingestion.list_loaded_scraped_products():
            category = category_from_payload(staged.raw_payload)
            source = sources.get(staged.product_source_id)
            if category and source:
                evidence[source.product_id][category.casefold()] = category
        categories = {category.name.casefold(): category for category in await uow.product_categories.list_active()}
        suggested = conflicts = 0
        for product_id, names in evidence.items():
            product = await uow.products.get_by_id(product_id)
            if product is None or not product.active or product.category_id:
                continue
            if len(names) != 1:
                conflicts += 1
                continue
            key, name = next(iter(names.items()))
            suggested += 1
            if apply:
                category = categories.get(key)
                if category is None:
                    category = await uow.product_categories.save(ProductCategory(uuid4(), name))
                    categories[key] = category
                product.category_id = category.id
                await uow.products.save(product)
        if apply:
            await uow.commit()
        print(f"Categories: {suggested} {'applied' if apply else 'suggested'}, {conflicts} conflicts skipped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args().apply))
