"""Deterministic, ambiguity-aware matching to canonical catalog products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.catalog.domain.entities import Product

from .product_normalizer import (
    ProductIdentity,
    build_product_identity,
    normalized_token_set,
    product_matching_key,
)


@dataclass(frozen=True)
class ProductIdentityCandidate:
    product: Product
    brand_name: str | None = None


@dataclass(frozen=True)
class ProductIdentityMatch:
    product: Product
    confidence: Decimal
    method: str


class ProductIdentityMatcher:
    """Matches only exact or structurally equivalent, non-ambiguous products."""

    def match(
        self,
        *,
        name: str,
        presentation: str | None,
        brand: str | None,
        candidates: list[ProductIdentityCandidate],
    ) -> ProductIdentityMatch | None:
        source_key = product_matching_key(name)
        exact = [
            candidate
            for candidate in candidates
            if product_matching_key(candidate.product.normalized_name) == source_key
            and self._brands_are_compatible(brand, candidate.brand_name)
        ]
        if len(exact) == 1:
            return ProductIdentityMatch(
                product=exact[0].product,
                confidence=Decimal("0.950"),
                method="exact_key",
            )
        if len(exact) > 1:
            return None

        source_identity = build_product_identity(name, presentation=presentation)
        structured = [
            candidate
            for candidate in candidates
            if self._is_structurally_equivalent(
                source_identity=source_identity,
                source_name=name,
                source_brand=brand,
                candidate=candidate,
            )
        ]
        if len(structured) != 1:
            return None
        return ProductIdentityMatch(
            product=structured[0].product,
            confidence=Decimal("0.900"),
            method="structured",
        )

    @staticmethod
    def _is_structurally_equivalent(
        *,
        source_identity: ProductIdentity,
        source_name: str,
        source_brand: str | None,
        candidate: ProductIdentityCandidate,
    ) -> bool:
        product_identity = build_product_identity(
            candidate.product.normalized_name,
            unit_measure=candidate.product.unit_measure,
            net_content=candidate.product.net_content,
        )
        if source_identity.quantity is None or product_identity.quantity is None:
            return False
        if source_identity.quantity != product_identity.quantity:
            return False

        canonical_brand = normalized_token_set(candidate.brand_name)
        extracted_brand = normalized_token_set(source_brand)
        if not ProductIdentityMatcher._brands_are_compatible(
            source_brand,
            candidate.brand_name,
        ):
            return False

        source_name_tokens = normalized_token_set(source_name)
        brand_evidence = not canonical_brand or bool(canonical_brand <= source_name_tokens) or (
            canonical_brand == extracted_brand
        )
        if not brand_evidence:
            return False

        source_tokens = source_identity.tokens - canonical_brand - extracted_brand
        product_tokens = product_identity.tokens - canonical_brand
        return source_tokens == product_tokens

    @staticmethod
    def _brands_are_compatible(source_brand: str | None, canonical_brand: str | None) -> bool:
        source_tokens = normalized_token_set(source_brand)
        canonical_tokens = normalized_token_set(canonical_brand)
        return not source_tokens or not canonical_tokens or source_tokens == canonical_tokens
