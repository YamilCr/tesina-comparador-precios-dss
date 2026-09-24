"""Read-only audit of substitution coverage against the configured database."""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.shared.infrastructure.database import async_session_factory, async_engine
from app.shared.infrastructure.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.modules.catalog.infrastructure.persistence import BrandModel
from app.modules.decision.application.branch_prices import load_branch_prices
from app.modules.decision.domain.services.substitution_policy import signature, compatible


async def main(query):
    async with async_session_factory() as session:
        brands = {b.id: b.nombre for b in (await session.scalars(select(BrandModel))).all()}
    async with SQLAlchemyUnitOfWork(async_session_factory) as uow:
        products = await uow.products.list_active(limit=10000)
        sigs = {p.id: signature(p, brands.get(p.brand_id)) for p in products}
        branches = await uow.branches.list_active()
        chains = {b.supermarket_id: b for b in branches if b.coordinates_verified}
        coverage = {}
        examples = []
        for chain_id, branch in chains.items():
            sources = await uow.product_sources.find_by_supermarket(chain_id)
            ids = list({s.product_id for s in sources if s.active})
            pricing = await load_branch_prices(
                uow, ids, {branch.id: branch}, datetime.now(timezone.utc), 14, publications=sources
            )
            chain = await uow.supermarkets.get_by_id(chain_id)
            coverage[chain.name] = {
                "branch_id": str(branch.id),
                "products": len(ids),
                "eligible": len(pricing.selected.get(branch.id, {})),
                "stale": len(pricing.quality.stale),
                "suspect": len(pricing.quality.suspect),
            }
            priced = pricing.selected.get(branch.id, {})
            chain_examples = 0
            for p in products:
                if p.id in priced:
                    continue
                for other in products:
                    if other.id in priced and compatible(
                        p, other, brands.get(p.brand_id), brands.get(other.brand_id)
                    ):
                        if chain_examples < 2:
                            examples.append(
                                {
                                    "chain": chain.name,
                                    "branch_id": str(branch.id),
                                    "original_id": str(p.id),
                                    "original": p.normalized_name,
                                    "replacement": other.normalized_name,
                                }
                            )
                        chain_examples += 1
            coverage[chain.name]["substitution_pairs"] = chain_examples
        print(
            json.dumps(
                {
                    "engine": async_engine.dialect.name,
                    "products": len(products),
                    "signatures": sum(s is not None for s in sigs.values()),
                    "coverage": coverage,
                },
                ensure_ascii=False,
            )
        )
        print(json.dumps({"live_examples": examples}, ensure_ascii=False))
        for p in products:
            if query.casefold() not in p.normalized_name.casefold():
                continue
            sig = sigs[p.id]
            matches = [
                other.normalized_name
                for other in products
                if compatible(p, other, brands.get(p.brand_id), brands.get(other.brand_id))
            ]
            print(
                json.dumps(
                    {
                        "id": str(p.id),
                        "name": p.normalized_name,
                        "brand": brands.get(p.brand_id),
                        "description": p.description,
                        "unit": p.unit_measure,
                        "content": str(p.net_content),
                        "signature": str(sig),
                        "compatible": matches,
                    },
                    ensure_ascii=False,
                )
            )
    await async_engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="arroz")
    asyncio.run(main(parser.parse_args().query))
