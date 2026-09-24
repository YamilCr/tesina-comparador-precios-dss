"""Audited repair of the verified 9 de Oro sconcitos 200 g presentation."""

import argparse
import asyncio
from decimal import Decimal
from uuid import uuid4

from app.modules.ingestion.domain.entities import ProductIdentityReview
from app.modules.ingestion.application.use_cases import DecideProductIdentityReviewUseCase
from app.modules.ingestion.infrastructure.etl import build_product_identity, normalized_brand_key
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


async def main(apply: bool) -> None:
    uow = SQLAlchemyUnitOfWork(async_session_factory)
    pending = []
    async with uow as tx:
        brands = await tx.brands.list_active()
        brand = next(b for b in brands if normalized_brand_key(b.name) == "9deoro")
        products = await tx.products.list_active(limit=100_000)
        group = []
        for product in products:
            identity = build_product_identity(product.normalized_name,
                unit_measure=product.unit_measure, net_content=product.net_content)
            if (identity.tokens == frozenset({"9", "oro", "sconcitos"})
                and identity.quantity and identity.quantity.unit == "g"
                and identity.quantity.amount == Decimal("200")
                and identity.pack_size in (None, 1)
                and product.brand_id in (None, brand.id)):
                group.append(product)
        if len(group) < 2:
            print(f"Active matching products: {len(group)}; no duplicates to repair.")
            return
        sources = await tx.product_sources.list_all()
        target = min(group, key=lambda p: (
            -sum(s.product_id == p.id for s in sources), p.brand_id is None,
            len(p.normalized_name), str(p.id)))
        print(f"Keep: {target.id} | {target.normalized_name}")
        reviews = await tx.ingestion.list_identity_reviews()
        for product in group:
            if product.id == target.id:
                continue
            print(f"Merge: {product.id} | {product.normalized_name}")
            if not apply:
                continue
            review = next((r for r in reviews if r.source_product_id == product.id
                and r.target_product_id == target.id and r.evidence_value == "verified:9deoro:sconcitos:200g:v1"), None)
            if review and review.status != "pending":
                raise ValueError("A prior decision exists; review manually before retrying.")
            if review is None:
                review = ProductIdentityReview(
                    id=uuid4(), review_type="semantic_alias", source_product_id=product.id,
                    target_product_id=target.id, evidence_value="verified:9deoro:sconcitos:200g:v1",
                    confidence=Decimal("0.950"),
                    rationale="Verified names and packaging: Scons/Sconcitos/Bizcochos Sconcitos 9 de Oro, single 200 g package.",
                )
                await tx.ingestion.save_identity_review(review)
            pending.append(review.id)
        if apply:
            target.brand_id = brand.id
            await tx.products.save(target)
            await tx.commit()
    for review_id in pending:
        result = await DecideProductIdentityReviewUseCase(uow).execute(
            review_id, decision="approve", note="Repair requested after checking the three publications and matching package images; retain all source price histories.")
        print(f"Approved {review_id}: {result.reassigned_sources} publications reassigned.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args().apply))
