"""Generates and decides auditable assisted canonical identity reviews."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.catalog.domain.entities import Product, ProductSource
from app.modules.ingestion.domain.entities import ProductIdentityReview
from app.modules.ingestion.infrastructure.etl import (
    build_product_identity,
    product_matching_key,
)
from app.shared.application import UnitOfWorkPort

from .enrich_product_catalog import _gtin_suggestions


@dataclass(frozen=True)
class IdentityReviewGenerationDTO:
    generated: int
    pending: int
    gtin_candidates: int
    semantic_candidates: int


@dataclass(frozen=True)
class IdentityReviewDecisionDTO:
    review: ProductIdentityReview
    reassigned_sources: int
    deactivated_product: bool


class GenerateProductIdentityReviewsUseCase:
    """Persists non-duplicated review proposals without applying any merge."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self) -> IdentityReviewGenerationDTO:
        async with self._unit_of_work as uow:
            products = await uow.products.list_active(limit=10_000)
            sources = [source for source in await uow.product_sources.list_all() if source.active]
            evidence = await uow.ingestion.list_loaded_scraped_products()
            reviews = await uow.ingestion.list_identity_reviews()
            products_by_id = {product.id: product for product in products}
            sources_by_id = {source.id: source for source in sources}
            sources_by_product = _sources_by_product(sources)
            existing_keys = {_review_key(review) for review in reviews}
            proposed_pairs = {
                frozenset((review.source_product_id, review.target_product_id))
                for review in reviews
                if review.review_type == "gtin_conflict"
            }
            generated = 0
            gtin_generated = 0
            semantic_generated = 0

            _, gtin_conflicts = _gtin_suggestions(
                evidence=evidence,
                sources_by_id=sources_by_id,
            )
            for conflict in gtin_conflicts:
                conflict_products = [
                    products_by_id[product_id]
                    for product_id in conflict.product_ids
                    if product_id in products_by_id
                ]
                if len(conflict_products) < 2:
                    continue
                target = _select_target(conflict_products, sources_by_product)
                for source_product in conflict_products:
                    if source_product.id == target.id:
                        continue
                    review = ProductIdentityReview(
                        id=uuid4(),
                        review_type="gtin_conflict",
                        source_product_id=source_product.id,
                        target_product_id=target.id,
                        evidence_value=conflict.gtin,
                        confidence=Decimal("0.980"),
                        rationale=(
                            "The same declared, checksum-valid GTIN is linked to different "
                            "active products and requires packaging/name review."
                        ),
                    )
                    key = _review_key(review)
                    if key in existing_keys:
                        continue
                    await uow.ingestion.save_identity_review(review)
                    existing_keys.add(key)
                    proposed_pairs.add(frozenset((source_product.id, target.id)))
                    generated += 1
                    gtin_generated += 1

            for group in _semantic_groups(products).values():
                if len(group) < 2:
                    continue
                target = _select_target(group, sources_by_product)
                for source_product in group:
                    if source_product.id == target.id:
                        continue
                    pair = frozenset((source_product.id, target.id))
                    if pair in proposed_pairs:
                        continue
                    review = ProductIdentityReview(
                        id=uuid4(),
                        review_type="semantic_alias",
                        source_product_id=source_product.id,
                        target_product_id=target.id,
                        evidence_value=_semantic_evidence(source_product),
                        confidence=Decimal("0.900"),
                        rationale=(
                            "Brand and package quantity agree after controlled aliases: "
                            "sin azucar=zero and liviano=light."
                        ),
                    )
                    key = _review_key(review)
                    if key in existing_keys:
                        continue
                    await uow.ingestion.save_identity_review(review)
                    existing_keys.add(key)
                    generated += 1
                    semantic_generated += 1
            if generated:
                await uow.commit()
            pending = await uow.ingestion.list_identity_reviews(status="pending")

        return IdentityReviewGenerationDTO(
            generated=generated,
            pending=len(pending),
            gtin_candidates=gtin_generated,
            semantic_candidates=semantic_generated,
        )


class DecideProductIdentityReviewUseCase:
    """Approves one merge or records its rejection with a mandatory note."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        review_id: UUID,
        *,
        decision: str,
        note: str,
    ) -> IdentityReviewDecisionDTO:
        if decision not in {"approve", "reject"}:
            raise ValueError("Decision must be approve or reject.")
        now = datetime.now(timezone.utc)
        async with self._unit_of_work as uow:
            review = await uow.ingestion.get_identity_review(review_id)
            if review is None:
                raise ValueError("Product identity review not found.")
            source_product = await uow.products.get_by_id(review.source_product_id)
            target_product = await uow.products.get_by_id(review.target_product_id)
            if source_product is None or target_product is None:
                raise ValueError("Reviewed product no longer exists.")

            reassigned = 0
            deactivated = False
            if decision == "approve":
                if not source_product.active or not target_product.active:
                    raise ValueError("Both reviewed products must be active before approval.")
                product_sources = await uow.product_sources.list_all()
                for product_source in product_sources:
                    if product_source.product_id != source_product.id:
                        continue
                    product_source.product_id = target_product.id
                    product_source.match_confidence = review.confidence
                    await uow.product_sources.save(product_source)
                    reassigned += 1
                _complete_target_metadata(target_product, source_product)
                await uow.products.save(target_product)
                source_product.deactivate()
                await uow.products.save(source_product)
                review.approve(note, now)
                deactivated = True
            else:
                review.reject(note, now)
            review = await uow.ingestion.save_identity_review(review)
            await uow.commit()

        return IdentityReviewDecisionDTO(
            review=review,
            reassigned_sources=reassigned,
            deactivated_product=deactivated,
        )


def _review_key(review: ProductIdentityReview) -> tuple[str, UUID, UUID, str]:
    return (
        review.review_type,
        review.source_product_id,
        review.target_product_id,
        review.evidence_value,
    )


def _sources_by_product(sources: list[ProductSource]) -> dict[UUID, list[ProductSource]]:
    grouped: dict[UUID, list[ProductSource]] = defaultdict(list)
    for source in sources:
        grouped[source.product_id].append(source)
    return grouped


def _select_target(
    products: list[Product],
    sources_by_product: dict[UUID, list[ProductSource]],
) -> Product:
    return min(
        products,
        key=lambda product: (
            -_metadata_score(product),
            -len(sources_by_product.get(product.id, [])),
            len(product.normalized_name),
            product.normalized_name.casefold(),
            str(product.id),
        ),
    )


def _metadata_score(product: Product) -> int:
    return sum(
        value is not None
        for value in (
            product.internal_code,
            product.category_id,
            product.brand_id,
            product.unit_measure,
            product.net_content,
        )
    )


def _semantic_groups(products: list[Product]) -> dict[tuple, list[Product]]:
    groups: dict[tuple, list[Product]] = defaultdict(list)
    for product in products:
        if product.brand_id is None:
            continue
        identity = build_product_identity(
            product.normalized_name,
            unit_measure=product.unit_measure,
            net_content=product.net_content,
        )
        if identity.quantity is None:
            continue
        tokens = _semantic_tokens(identity.tokens)
        signature = (
            product.brand_id,
            tuple(sorted(tokens)),
            identity.quantity.unit,
            identity.quantity.amount,
            identity.pack_size,
        )
        groups[signature].append(product)
    return {
        signature: group
        for signature, group in groups.items()
        if len({product_matching_key(product.normalized_name) for product in group}) > 1
    }


def _semantic_tokens(tokens: frozenset[str]) -> frozenset[str]:
    normalized = set(tokens)
    if {"sin", "azucar"} <= normalized:
        normalized.difference_update({"sin", "azucar"})
        normalized.add("zero")
    if "liviano" in normalized:
        normalized.remove("liviano")
        normalized.add("light")
    return frozenset(normalized)


def _semantic_evidence(product: Product) -> str:
    identity = build_product_identity(
        product.normalized_name,
        unit_measure=product.unit_measure,
        net_content=product.net_content,
    )
    tokens = " ".join(sorted(_semantic_tokens(identity.tokens)))
    quantity = identity.quantity
    return f"brand={product.brand_id};tokens={tokens};quantity={quantity.amount}{quantity.unit}"


def _complete_target_metadata(target: Product, source: Product) -> None:
    if target.category_id is None:
        target.category_id = source.category_id
    if target.brand_id is None:
        target.brand_id = source.brand_id
    if target.unit_measure is None:
        target.unit_measure = source.unit_measure
    if target.net_content is None:
        target.net_content = source.net_content
