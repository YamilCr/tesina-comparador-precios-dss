"""Shared branch pricing: quality checks, direct price priority and chain fallback."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.modules.catalog.domain.entities import ProductSource
from app.modules.prices.domain.entities import Price
from app.modules.prices.domain.services import PriceQualityPolicy, PriceQualitySelection
from app.modules.supermarkets.domain.entities import Branch
from app.shared.application import UnitOfWorkPort


def better_price(candidate: Price, current: Price | None) -> bool:
    return (
        current is None
        or candidate.observed_at > current.observed_at
        or (candidate.observed_at == current.observed_at and candidate.amount < current.amount)
    )


def select_branch_prices(
    prices: list[Price],
    branch_by_id: dict[UUID, Branch],
    source_by_id: dict[UUID, ProductSource],
    source_product_ids: dict[UUID, UUID],
) -> dict[UUID, dict[UUID, Price]]:
    selected, by_chain = {}, {}
    for price in prices:
        source = source_by_id.get(price.product_source_id)
        product_id = source_product_ids.get(price.product_source_id)
        if not price.available or source is None or product_id is None:
            continue
        key = (source.supermarket_id, product_id)
        if better_price(price, by_chain.get(key)):
            by_chain[key] = price
        branch = branch_by_id.get(price.branch_id)
        if branch is not None and source.supermarket_id == branch.supermarket_id:
            branch_prices = selected.setdefault(branch.id, {})
            if better_price(price, branch_prices.get(product_id)):
                branch_prices[product_id] = price
    for branch in branch_by_id.values():
        branch_prices = selected.setdefault(branch.id, {})
        for (chain_id, product_id), price in by_chain.items():
            if chain_id == branch.supermarket_id and product_id not in branch_prices:
                branch_prices[product_id] = price
    return selected


@dataclass
class BranchPrices:
    selected: dict[UUID, dict[UUID, Price]]
    quality: PriceQualitySelection
    reasons: dict[tuple[UUID, UUID], str]


async def load_branch_prices(
    uow: UnitOfWorkPort,
    product_ids: list[UUID],
    branches: dict[UUID, Branch],
    evaluated_at: datetime,
    max_age_days: int,
    publications: list[ProductSource] | None = None,
) -> BranchPrices:
    if publications is None:
        publications = []
        for product_id in product_ids:
            publications.extend(await uow.product_sources.find_by_product(product_id))
    sources = {source.id: source for source in publications if source.active}
    chains = {branch.supermarket_id for branch in branches.values()}
    product_by_source = {key: source.product_id for key, source in sources.items()}
    prices = [
        price
        for price in await uow.prices.find_for_basket(product_ids=list(product_ids))
        if price.product_source_id in sources
        and sources[price.product_source_id].supermarket_id in chains
    ]
    quality = PriceQualityPolicy(max_age_days=max_age_days).evaluate(prices, as_of=evaluated_at)
    selected = select_branch_prices(quality.eligible, branches, sources, product_by_source)
    reasons = {}
    for status, excluded in (("stale", quality.stale), ("suspect", quality.suspect)):
        for price in excluded:
            source = sources[price.product_source_id]
            for branch in branches.values():
                if source.supermarket_id == branch.supermarket_id:
                    reasons[(branch.id, source.product_id)] = status
    return BranchPrices(selected, quality, reasons)
