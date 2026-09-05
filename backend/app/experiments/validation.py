"""Metrics for performance, chain coverage, identity quality, and DSS sensitivity."""

from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import fmean, median, stdev
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.catalog.domain.entities import Product
from app.modules.catalog.infrastructure.persistence import ProductModel, ProductSourceModel
from app.modules.decision.domain.entities import Alternative
from app.modules.decision.domain.services import WeightedSumModel
from app.modules.decision.domain.value_objects import CriteriaWeights
from app.modules.ingestion.infrastructure.etl import (
    ProductIdentityCandidate,
    ProductIdentityMatcher,
)
from app.modules.ingestion.infrastructure.persistence import (
    ScrapedProductModel,
    ScrapingRunModel,
    ScrapingSourceModel,
)
from app.modules.prices.infrastructure.persistence import PriceModel
from app.modules.supermarkets.infrastructure.persistence import BranchModel, SupermarketModel


def _safe_rate(numerator: float, denominator: float) -> float:
    return round((numerator / denominator) * 100, 3) if denominator else 0.0


def _describe(values: list[float]) -> dict[str, float | int]:
    ordered = sorted(values)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "samples": len(values),
        "mean": round(fmean(values), 3),
        "median": round(median(values), 3),
        "stdev": round(stdev(values), 3) if len(values) > 1 else 0.0,
        "p95": round(ordered[p95_index], 3),
        "min": round(ordered[0], 3),
        "max": round(ordered[-1], 3),
    }


def analyze_benchmark(path: Path) -> tuple[list[dict], dict]:
    """Calculates descriptive and paired statistics from an aggregate benchmark CSV."""
    with path.open(encoding="utf-8-sig", newline="") as source:
        records = list(csv.DictReader(source))
    if not records:
        raise ValueError("Benchmark CSV has no records.")

    by_mode: dict[str, list[dict]] = defaultdict(list)
    by_iteration: dict[str, dict[str, float]] = defaultdict(dict)
    for row in records:
        mode = row["mode"]
        if mode not in {"sequential", "concurrent"}:
            raise ValueError(f"Unsupported benchmark mode: {mode}.")
        by_mode[mode].append(row)
        by_iteration[row["iteration"]][mode] = float(row["duration_ms"])
    if not by_mode["sequential"] or not by_mode["concurrent"]:
        raise ValueError("Benchmark requires sequential and concurrent records.")

    sequential_mean = fmean(float(row["duration_ms"]) for row in by_mode["sequential"])
    concurrent_mean = fmean(float(row["duration_ms"]) for row in by_mode["concurrent"])
    paired_reductions = [
        ((modes["sequential"] - modes["concurrent"]) / modes["sequential"]) * 100
        for modes in by_iteration.values()
        if "sequential" in modes and "concurrent" in modes and modes["sequential"]
    ]
    summary_rows = []
    for mode in ("sequential", "concurrent"):
        rows = by_mode[mode]
        stats = _describe([float(row["duration_ms"]) for row in rows])
        scraped = sum(int(row.get("items_scraped", 0)) for row in rows)
        elapsed_seconds = sum(float(row["duration_ms"]) for row in rows) / 1000
        summary_rows.append(
            {
                "mode": mode,
                "samples": stats["samples"],
                "mean_duration_ms": stats["mean"],
                "median_duration_ms": stats["median"],
                "stdev_duration_ms": stats["stdev"],
                "p95_duration_ms": stats["p95"],
                "min_duration_ms": stats["min"],
                "max_duration_ms": stats["max"],
                "success_rate_pct": _safe_rate(
                    sum(int(row.get("failed_sources", 0)) == 0 for row in rows),
                    len(rows),
                ),
                "throughput_items_per_second": round(
                    scraped / elapsed_seconds if elapsed_seconds else 0,
                    3,
                ),
                "speedup_vs_sequential": round(
                    sequential_mean / concurrent_mean,
                    4,
                ),
                "mean_duration_reduction_pct": round(
                    ((sequential_mean - concurrent_mean) / sequential_mean) * 100,
                    3,
                ),
                "mean_paired_reduction_pct": round(fmean(paired_reductions), 3),
            }
        )
    summary = {
        "source_file": str(path),
        "iterations": len(paired_reductions),
        "speedup": round(sequential_mean / concurrent_mean, 4),
        "duration_reduction_pct": round(
            ((sequential_mean - concurrent_mean) / sequential_mean) * 100,
            3,
        ),
        "paired_reduction_mean_pct": round(fmean(paired_reductions), 3),
        "paired_reduction_stdev_pct": (
            round(stdev(paired_reductions), 3) if len(paired_reductions) > 1 else 0.0
        ),
    }
    return summary_rows, summary


async def collect_chain_coverage(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[dict]:
    """Builds comparable coverage and ETL quality metrics for every active chain."""
    async with session_factory() as session:
        supermarkets = list(
            (
                await session.scalars(
                    select(SupermarketModel)
                    .where(SupermarketModel.activo.is_(True))
                    .order_by(SupermarketModel.nombre)
                )
            ).all()
        )
        total_products = int(
            await session.scalar(
                select(func.count(ProductModel.id)).where(ProductModel.activo.is_(True))
            )
            or 0
        )
        rows = []
        for supermarket in supermarkets:
            branch_rows = list(
                (
                    await session.scalars(
                        select(BranchModel).where(
                            BranchModel.supermercado_id == supermarket.id,
                            BranchModel.activo.is_(True),
                        )
                    )
                ).all()
            )
            source_rows = list(
                (
                    await session.scalars(
                        select(ScrapingSourceModel).where(
                            ScrapingSourceModel.supermercado_id == supermarket.id,
                            ScrapingSourceModel.activo.is_(True),
                        )
                    )
                ).all()
            )
            source_ids = [source.id for source in source_rows]
            run_statuses: Counter[str] = Counter()
            staging_statuses: Counter[str] = Counter()
            latest_success: datetime | None = None
            if source_ids:
                run_statuses.update(
                    dict(
                        (
                            await session.execute(
                                select(ScrapingRunModel.estado, func.count(ScrapingRunModel.id))
                                .where(ScrapingRunModel.scraping_source_id.in_(source_ids))
                                .group_by(ScrapingRunModel.estado)
                            )
                        ).all()
                    )
                )
                staging_statuses.update(
                    dict(
                        (
                            await session.execute(
                                select(
                                    ScrapedProductModel.estado,
                                    func.count(ScrapedProductModel.id),
                                )
                                .join(
                                    ScrapingRunModel,
                                    ScrapingRunModel.id
                                    == ScrapedProductModel.scraping_run_id,
                                )
                                .where(ScrapingRunModel.scraping_source_id.in_(source_ids))
                                .group_by(ScrapedProductModel.estado)
                            )
                        ).all()
                    )
                )
                latest_success = await session.scalar(
                    select(func.max(ScrapingRunModel.finalizado_en)).where(
                        ScrapingRunModel.scraping_source_id.in_(source_ids),
                        ScrapingRunModel.estado == "succeeded",
                    )
                )

            product_ids = set(
                (
                    await session.scalars(
                        select(ProductSourceModel.producto_id).where(
                            ProductSourceModel.supermercado_id == supermarket.id,
                            ProductSourceModel.activo.is_(True),
                        )
                    )
                ).all()
            )
            price_pairs = set(
                (
                    await session.execute(
                        select(ProductSourceModel.producto_id, PriceModel.sucursal_id)
                        .join(
                            PriceModel,
                            PriceModel.producto_fuente_id == ProductSourceModel.id,
                        )
                        .where(
                            ProductSourceModel.supermercado_id == supermarket.id,
                            PriceModel.disponible.is_(True),
                        )
                    )
                ).all()
            )
            price_observations = int(
                await session.scalar(
                    select(func.count(PriceModel.id))
                    .join(
                        ProductSourceModel,
                        ProductSourceModel.id == PriceModel.producto_fuente_id,
                    )
                    .where(
                        ProductSourceModel.supermercado_id == supermarket.id,
                        PriceModel.disponible.is_(True),
                    )
                )
                or 0
            )
            priced_products = {product_id for product_id, _ in price_pairs}
            total_runs = sum(run_statuses.values())
            total_staging = sum(staging_statuses.values())
            denominator_pairs = len(branch_rows) * len(product_ids)
            rows.append(
                {
                    "supermarket_id": str(supermarket.id),
                    "chain": supermarket.nombre,
                    "active_branches": len(branch_rows),
                    "verified_branches": sum(
                        branch.coordenadas_verificadas for branch in branch_rows
                    ),
                    "active_scraping_sources": len(source_rows),
                    "scraping_runs": total_runs,
                    "successful_runs": run_statuses["succeeded"],
                    "failed_runs": run_statuses["failed"],
                    "run_success_rate_pct": _safe_rate(
                        run_statuses["succeeded"],
                        total_runs,
                    ),
                    "staged_items": total_staging,
                    "loaded_items": staging_statuses["loaded"],
                    "rejected_items": staging_statuses["rejected"],
                    "duplicate_items": staging_statuses["duplicate"],
                    "unmatched_items": staging_statuses["unmatched"],
                    "etl_acceptance_rate_pct": _safe_rate(
                        staging_statuses["loaded"],
                        total_staging,
                    ),
                    "published_canonical_products": len(product_ids),
                    "catalog_coverage_pct": _safe_rate(len(product_ids), total_products),
                    "products_with_available_price": len(priced_products),
                    "priced_catalog_coverage_pct": _safe_rate(
                        len(priced_products),
                        len(product_ids),
                    ),
                    "available_price_observations": price_observations,
                    "branch_product_coverage_pct": _safe_rate(
                        len(price_pairs),
                        denominator_pairs,
                    ),
                    "latest_successful_run_at": (
                        latest_success.isoformat() if latest_success is not None else ""
                    ),
                }
            )
        return rows


def analyze_matching_quality(
    catalog_path: Path,
    ground_truth_path: Path,
) -> tuple[list[dict], list[dict], dict]:
    """Evaluates canonical identity matching against a versioned labeled dataset."""
    with catalog_path.open(encoding="utf-8-sig", newline="") as source:
        catalog_rows = list(csv.DictReader(source))
    candidates = [
        ProductIdentityCandidate(
            product=Product(
                id=uuid5(NAMESPACE_URL, row["internal_code"]),
                normalized_name=row["normalized_name"],
                unit_measure=row["unit_measure"] or None,
                net_content=Decimal(row["net_content"]) if row["net_content"] else None,
                internal_code=row["internal_code"],
            ),
            brand_name=row["brand"] or None,
        )
        for row in catalog_rows
    ]
    with ground_truth_path.open(encoding="utf-8-sig", newline="") as source:
        cases = list(csv.DictReader(source))

    matcher = ProductIdentityMatcher()
    details = []
    for case in cases:
        match = matcher.match(
            name=case["source_name"],
            presentation=case["presentation"] or None,
            brand=case["source_brand"] or None,
            candidates=candidates,
        )
        predicted = match.product.internal_code if match is not None else ""
        expected = case["expected_internal_code"]
        if expected and predicted == expected:
            outcome = "true_positive"
        elif expected and predicted:
            outcome = "wrong_identity"
        elif expected:
            outcome = "false_negative"
        elif predicted:
            outcome = "false_positive"
        else:
            outcome = "true_negative"
        details.append(
            {
                **case,
                "predicted_internal_code": predicted,
                "match_method": match.method if match is not None else "abstain",
                "confidence": str(match.confidence) if match is not None else "",
                "outcome": outcome,
                "correct": predicted == expected,
            }
        )

    summary_rows = [_matching_summary_row("overall", details)]
    for group in sorted({row["case_group"] for row in details}):
        summary_rows.append(
            _matching_summary_row(
                group,
                [row for row in details if row["case_group"] == group],
            )
        )
    overall = summary_rows[0]
    summary = {
        "cases": overall["cases"],
        "precision": overall["precision"],
        "recall": overall["recall"],
        "f1": overall["f1"],
        "accuracy": overall["accuracy"],
        "abstention_rate_pct": overall["abstention_rate_pct"],
        "catalog_entries": len(candidates),
    }
    return details, summary_rows, summary


def _matching_summary_row(group: str, rows: list[dict]) -> dict:
    tp = sum(row["outcome"] == "true_positive" for row in rows)
    tn = sum(row["outcome"] == "true_negative" for row in rows)
    wrong = sum(row["outcome"] == "wrong_identity" for row in rows)
    fp = sum(row["outcome"] == "false_positive" for row in rows) + wrong
    fn = sum(row["outcome"] == "false_negative" for row in rows) + wrong
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    abstentions = sum(not row["predicted_internal_code"] for row in rows)
    return {
        "case_group": group,
        "cases": len(rows),
        "true_positives": tp,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "wrong_identity": wrong,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round((tp + tn) / len(rows), 4) if rows else 0.0,
        "abstention_rate_pct": _safe_rate(abstentions, len(rows)),
    }


def analyze_weight_sensitivity(
    scenario_path: Path,
    *,
    step: Decimal = Decimal("0.05"),
    baseline: tuple[Decimal, Decimal, Decimal] = (
        Decimal("0.60"),
        Decimal("0.30"),
        Decimal("0.10"),
    ),
) -> tuple[list[dict], list[dict], dict]:
    """Sweeps the full weight simplex and measures top-rank and order stability."""
    units = int(Decimal("1") / step)
    if step <= 0 or step * units != Decimal("1"):
        raise ValueError("Weight step must divide one exactly.")
    with scenario_path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    alternatives = [
        Alternative(
            branch_id=uuid5(NAMESPACE_URL, row["alternative_key"]),
            supermarket_name=row["supermarket_name"],
            branch_name=row["branch_name"],
            total_cost=Decimal(row["total_cost"]),
            distance_km=Decimal(row["distance_km"]),
            saving=Decimal(row["saving"]),
        )
        for row in rows
    ]
    labels = {
        alternative.branch_id: f"{alternative.supermarket_name} - {alternative.branch_name}"
        for alternative in alternatives
    }
    model = WeightedSumModel()
    baseline_weights = CriteriaWeights(
        price=baseline[0],
        distance=baseline[1],
        saving=baseline[2],
    )
    baseline_ranking = model.rank(alternatives, baseline_weights)
    baseline_positions = {
        result.branch_id: result.position for result in baseline_ranking
    }
    baseline_winner = labels[baseline_ranking[0].branch_id]

    details = []
    winner_counts: Counter[str] = Counter()
    correlations = []
    for price_units in range(units + 1):
        for distance_units in range(units - price_units + 1):
            saving_units = units - price_units - distance_units
            weights = CriteriaWeights(
                price=step * price_units,
                distance=step * distance_units,
                saving=step * saving_units,
            )
            ranking = model.rank(alternatives, weights)
            winner = labels[ranking[0].branch_id]
            winner_counts[winner] += 1
            correlation = _spearman(
                baseline_positions,
                {result.branch_id: result.position for result in ranking},
            )
            correlations.append(correlation)
            details.append(
                {
                    "price_weight": str(weights.price),
                    "distance_weight": str(weights.distance),
                    "saving_weight": str(weights.saving),
                    "winner": winner,
                    "winner_score": str(ranking[0].score.quantize(Decimal("0.000001"))),
                    "same_as_baseline": winner == baseline_winner,
                    "spearman_vs_baseline": round(correlation, 6),
                    "ranking": ";".join(
                        f"{result.position}:{labels[result.branch_id]}" for result in ranking
                    ),
                }
            )
    winner_rows = [
        {
            "winner": winner,
            "scenarios_won": count,
            "scenario_share_pct": _safe_rate(count, len(details)),
        }
        for winner, count in winner_counts.most_common()
    ]
    same_winner = winner_counts[baseline_winner]
    summary = {
        "scenarios": len(details),
        "alternatives": len(alternatives),
        "weight_step": str(step),
        "baseline_weights": [str(value) for value in baseline],
        "baseline_winner": baseline_winner,
        "baseline_winner_robustness_pct": _safe_rate(same_winner, len(details)),
        "distinct_winners": len(winner_counts),
        "mean_spearman_vs_baseline": round(fmean(correlations), 4),
        "minimum_spearman_vs_baseline": round(min(correlations), 4),
    }
    return details, winner_rows, summary


def _spearman(first: dict, second: dict) -> float:
    keys = list(first)
    count = len(keys)
    if count < 2:
        return 1.0
    squared_distance = sum((first[key] - second[key]) ** 2 for key in keys)
    return 1 - ((6 * squared_distance) / (count * (count**2 - 1)))


def write_csv(path: Path, rows: list[dict]) -> None:
    """Writes homogeneous metric rows with stable UTF-8 CSV encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"Cannot write an empty experimental dataset: {path.name}.")
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
