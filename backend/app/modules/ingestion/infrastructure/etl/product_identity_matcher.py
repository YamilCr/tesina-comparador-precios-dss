"""Deterministic, ambiguity-aware matching to canonical catalog products."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from rapidfuzz import fuzz

from app.modules.catalog.domain.entities import Product

from .product_normalizer import (
    PackageQuantity,
    ProductIdentity,
    build_product_identity,
    normalized_brand_key,
    normalized_token_set,
)

FUZZY_AUTOMATCH_THRESHOLD = Decimal("0.920")
FUZZY_CONFIDENCE_CAP = Decimal("0.899")
VARIANT_TOKENS = frozenset(
    {
        "azucar",
        "descremada",
        "diet",
        "entera",
        "integral",
        "lactosa",
        "light",
        "liviano",
        "sin",
        "zero",
    }
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
    """Matches only exact or structurally compatible, non-ambiguous products."""

    def match(
        self,
        *,
        name: str,
        presentation: str | None,
        brand: str | None,
        candidates: list[ProductIdentityCandidate],
    ) -> ProductIdentityMatch | None:
        source_identity = build_product_identity(name, presentation=presentation)
        source_signature = _identity_signature(source_identity)
        exact = []
        for candidate in candidates:
            product_identity = build_product_identity(
                candidate.product.normalized_name,
                unit_measure=candidate.product.unit_measure,
                net_content=candidate.product.net_content,
            )
            if (
                _identity_signature(product_identity) == source_signature
                and self._brands_are_compatible(brand, candidate.brand_name)
                and self._has_brand_evidence(
                    source_name=name,
                    source_brand=brand,
                    canonical_brand=candidate.brand_name,
                )
            ):
                exact.append(candidate)
        if len(exact) == 1:
            return ProductIdentityMatch(
                product=exact[0].product,
                confidence=Decimal("0.950"),
                method="exact_key",
            )
        if len(exact) > 1:
            return None

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
        if len(structured) == 1:
            return ProductIdentityMatch(
                product=structured[0].product,
                confidence=Decimal("0.900"),
                method="structured",
            )
        if len(structured) > 1:
            return None

        compatible = self._compatible_candidates(
            source_identity=source_identity,
            source_name=name,
            source_brand=brand,
            candidates=candidates,
        )
        return self._fuzzy_match(source_identity=source_identity, candidates=compatible)

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
        if not ProductIdentityMatcher._passes_hard_constraints(
            source_identity=source_identity,
            product_identity=product_identity,
            source_name=source_name,
            source_brand=source_brand,
            canonical_brand=candidate.brand_name,
        ):
            return False

        canonical_brand = normalized_token_set(candidate.brand_name)
        extracted_brand = normalized_token_set(source_brand)
        source_tokens = source_identity.tokens - canonical_brand - extracted_brand
        product_tokens = product_identity.tokens - canonical_brand
        return source_tokens == product_tokens

    @staticmethod
    def _compatible_candidates(
        *,
        source_identity: ProductIdentity,
        source_name: str,
        source_brand: str | None,
        candidates: list[ProductIdentityCandidate],
    ) -> list[tuple[ProductIdentityCandidate, ProductIdentity]]:
        compatible: list[tuple[ProductIdentityCandidate, ProductIdentity]] = []
        for candidate in candidates:
            product_identity = build_product_identity(
                candidate.product.normalized_name,
                unit_measure=candidate.product.unit_measure,
                net_content=candidate.product.net_content,
            )
            if ProductIdentityMatcher._passes_hard_constraints(
                source_identity=source_identity,
                product_identity=product_identity,
                source_name=source_name,
                source_brand=source_brand,
                canonical_brand=candidate.brand_name,
            ):
                compatible.append((candidate, product_identity))
        return compatible

    @staticmethod
    def _fuzzy_match(
        *,
        source_identity: ProductIdentity,
        candidates: list[tuple[ProductIdentityCandidate, ProductIdentity]],
    ) -> ProductIdentityMatch | None:
        if len(candidates) != 1:
            return None

        candidate, product_identity = candidates[0]
        score = ProductIdentityMatcher._lexical_similarity(source_identity, product_identity)
        if score < FUZZY_AUTOMATCH_THRESHOLD:
            return None
        return ProductIdentityMatch(
            product=candidate.product,
            confidence=min(score, FUZZY_CONFIDENCE_CAP),
            method="fuzzy_lexical",
        )

    @staticmethod
    def _passes_hard_constraints(
        *,
        source_identity: ProductIdentity,
        product_identity: ProductIdentity,
        source_name: str,
        source_brand: str | None,
        canonical_brand: str | None,
    ) -> bool:
        if source_identity.quantity is None or product_identity.quantity is None:
            return False
        if source_identity.quantity != product_identity.quantity:
            return False
        if _normalized_pack_size(source_identity.pack_size) != _normalized_pack_size(
            product_identity.pack_size
        ):
            return False
        if not ProductIdentityMatcher._brands_are_compatible(source_brand, canonical_brand):
            return False
        if not ProductIdentityMatcher._has_brand_evidence(
            source_name=source_name,
            source_brand=source_brand,
            canonical_brand=canonical_brand,
        ):
            return False
        return _variant_tokens(source_identity.tokens) == _variant_tokens(product_identity.tokens)

    @staticmethod
    def _brands_are_compatible(source_brand: str | None, canonical_brand: str | None) -> bool:
        source_tokens = normalized_token_set(source_brand)
        canonical_tokens = normalized_token_set(canonical_brand)
        return not source_tokens or not canonical_tokens or source_tokens == canonical_tokens

    @staticmethod
    def _has_brand_evidence(
        *,
        source_name: str,
        source_brand: str | None,
        canonical_brand: str | None,
    ) -> bool:
        canonical_tokens = normalized_token_set(canonical_brand)
        if not canonical_tokens:
            return True

        extracted_brand = normalized_token_set(source_brand)
        if canonical_tokens == extracted_brand:
            return True

        source_name_tokens = normalized_token_set(source_name)
        if canonical_tokens <= source_name_tokens:
            return True

        canonical_key = normalized_brand_key(canonical_brand)
        source_name_key = normalized_brand_key(source_name)
        return bool(canonical_key and canonical_key in source_name_key)

    @staticmethod
    def _lexical_similarity(left: ProductIdentity, right: ProductIdentity) -> Decimal:
        left_text = " ".join(sorted(left.tokens))
        right_text = " ".join(sorted(right.tokens))
        if not left_text or not right_text:
            return Decimal("0")

        token_score = Decimal(str(fuzz.token_set_ratio(left_text, right_text) / 100)).quantize(
            Decimal("0.001")
        )
        compact_score = Decimal(
            str(
                fuzz.ratio(
                    normalized_brand_key(left_text),
                    normalized_brand_key(right_text),
                )
                / 100
            )
        ).quantize(Decimal("0.001"))
        return max(token_score, compact_score)


def _normalized_pack_size(value: int | None) -> int | None:
    return None if value in (None, 1) else value


def _variant_tokens(tokens: frozenset[str]) -> frozenset[str]:
    return tokens & VARIANT_TOKENS


def _identity_signature(
    identity: ProductIdentity,
) -> tuple[frozenset[str], tuple[str, Decimal] | None, int | None]:
    return (
        identity.tokens,
        _quantity_signature(identity.quantity),
        _normalized_pack_size(identity.pack_size),
    )


def _quantity_signature(quantity: PackageQuantity | None) -> tuple[str, Decimal] | None:
    if quantity is None:
        return None
    return quantity.unit, quantity.amount
