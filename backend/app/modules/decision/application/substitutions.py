"""Read-only substitution suggestions and validation shared with ranking."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.modules.decision.application.branch_prices import load_branch_prices
from app.modules.decision.domain.services.substitution_policy import compatible, signature

logger = logging.getLogger(__name__)


class InvalidSubstitution(ValueError):
    def __init__(self, branch_id, original_product_id, message):
        super().__init__(message)
        self.detail = {
            "code": "invalid_substitution",
            "branch_id": str(branch_id),
            "original_product_id": str(original_product_id),
            "message": message,
        }


async def brand_names(uow, products):
    result = {}
    for brand_id in {p.brand_id for p in products if p.brand_id is not None}:
        brand = await uow.brands.get_by_id(brand_id)
        if brand:
            result[brand_id] = brand.name
    return result


def product_payload(product, brands):
    identity = signature(product, brands.get(product.brand_id))
    return {
        "id": str(product.id),
        "normalized_name": product.normalized_name,
        "brand_name": brands.get(product.brand_id),
        "image_url": product.image_url,
        "unit_measure": product.unit_measure,
        "net_content": str(product.net_content) if product.net_content is not None else None,
        "base_quantity": str(identity.amount) if identity else None,
        "base_unit": identity.unit if identity else None,
        "pack_size": identity.pack if identity else None,
    }


def candidate_payload(original_id, replacement, price, quantity, branch_id, brands):
    return {
        "original_product_id": str(original_id),
        "product": product_payload(replacement, brands),
        "quantity": str(quantity),
        "unit_price": str(price.amount),
        "subtotal": str(price.amount * quantity),
        "currency": price.currency,
        "observed_at": price.observed_at.isoformat(),
        "price_branch_id": str(price.branch_id),
        "inferred_from_chain": price.branch_id != branch_id,
        "compatibility_reason": "Igual cantidad, unidad y pack; descripciones compatibles tras normalizar escritura. Puede cambiar la marca.",
    }


async def validate_substitutions(uow, substitutions, product_ids, branches):
    replacements, seen = {}, set()
    for item in substitutions:
        key = (item.branch_id, item.original_product_id)

        def invalid(message):
            return InvalidSubstitution(*key, message)

        if key in seen:
            raise invalid("Reemplazo duplicado para la misma linea y sucursal.")
        seen.add(key)
        if item.branch_id not in branches:
            raise invalid("Sucursal no habilitada en esta evaluacion.")
        if item.original_product_id not in product_ids:
            raise invalid("El producto original no pertenece a la lista.")
        original = await uow.products.get_by_id(item.original_product_id)
        replacement = await uow.products.get_by_id(item.replacement_product_id)
        if original is None or not original.active:
            raise invalid("El producto original no existe o esta inactivo.")
        if replacement is None or not replacement.active:
            raise invalid("El reemplazo no existe o esta inactivo.")
        brands = await brand_names(uow, [original, replacement])
        if not compatible(
            original, replacement, brands.get(original.brand_id), brands.get(replacement.brand_id)
        ):
            raise invalid("El reemplazo no conserva tipo, variantes o presentacion.")
        replacements[key] = (replacement, brands)
    return replacements


class SuggestSubstitutionsUseCase:
    def __init__(self, uow, search_index=None):
        self.uow, self.search_index = uow, search_index

    async def execute(self, branch_id, items, *, as_of=None, max_price_age_days=14):
        evaluated_at = as_of or datetime.now(timezone.utc)
        async with self.uow as uow:
            branch = await uow.branches.get_by_id(branch_id)
            chain = await uow.supermarkets.get_by_id(branch.supermarket_id) if branch else None
            if (
                not branch
                or not branch.active
                or not branch.coordinates_verified
                or not chain
                or not chain.active
            ):
                raise ValueError("Sucursal no habilitada para comparar.")
            originals = {}
            for item in items:
                product = await uow.products.get_by_id(item.product_id)
                if not product or not product.active:
                    raise ValueError(f"Producto inexistente o inactivo: {item.product_id}")
                originals[product.id] = product
            sources = await uow.product_sources.find_by_supermarket(branch.supermarket_id)
            ids = list({source.product_id for source in sources if source.active})
            products = await uow.products.list_active_by_ids(ids)
            brands = await brand_names(uow, [*originals.values(), *products])
            pool = {p.id: p for p in products}
            pricing = await load_branch_prices(
                uow,
                list(set(ids) | set(originals)),
                {branch.id: branch},
                evaluated_at,
                max_price_age_days,
                publications=sources,
            )
            selected = pricing.selected.get(branch.id, {})
            groups = []
            for item in items:
                if item.product_id in selected:
                    continue
                original = originals[item.product_id]
                # Vector recall is optional; every hit must still belong to this chain's active pool.
                candidates = list(pool.values())
                if self.search_index is not None:
                    try:
                        hits = await self.search_index.search(original.normalized_name, top_k=50)
                        candidates = list(
                            {
                                p.id: p
                                for p in [
                                    *(
                                        pool[hit.product_id]
                                        for hit in hits
                                        if hit.product_id in pool
                                    ),
                                    *candidates,
                                ]
                            }.values()
                        )
                    except Exception:
                        logger.warning(
                            "Substitution vector retrieval failed; using structured candidates",
                            exc_info=True,
                        )
                compatible_products = [
                    p
                    for p in candidates
                    if compatible(
                        original, p, brands.get(original.brand_id), brands.get(p.brand_id)
                    )
                ]
                eligible = [
                    candidate_payload(
                        original.id, p, selected[p.id], item.quantity, branch.id, brands
                    )
                    for p in compatible_products
                    if p.id in selected
                ]
                eligible.sort(
                    key=lambda c: (
                        Decimal(c["subtotal"]),
                        c["product"]["normalized_name"].casefold(),
                        c["product"]["id"],
                    )
                )
                groups.append(
                    {
                        "original": product_payload(original, brands),
                        "quantity": str(item.quantity),
                        "reason": pricing.reasons.get((branch.id, original.id), "missing"),
                        "candidates": eligible[:3],
                        "diagnostics": {
                            "code": (
                                "available"
                                if eligible
                                else "insufficient_attributes"
                                if signature(original, brands.get(original.brand_id)) is None
                                else "no_chain_products"
                                if not pool
                                else "no_compatible_products"
                                if not compatible_products
                                else "no_suitable_prices"
                            ),
                            "compatible_products": len(compatible_products),
                            "stale_products": sum(
                                p.id not in selected
                                and pricing.reasons.get((branch.id, p.id)) == "stale"
                                for p in compatible_products
                            ),
                            "suspect_products": sum(
                                p.id not in selected
                                and pricing.reasons.get((branch.id, p.id)) == "suspect"
                                for p in compatible_products
                            ),
                            "max_price_age_days": max_price_age_days,
                        },
                    }
                )
            return {
                "branch_id": str(branch_id),
                "evaluated_at": evaluated_at.isoformat(),
                "items": groups,
            }
