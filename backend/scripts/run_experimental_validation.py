"""Generates the reproducible experimental evidence bundle used by the thesis."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from app.experiments import (
    analyze_benchmark,
    analyze_matching_quality,
    analyze_weight_sensitivity,
    collect_chain_coverage,
    write_csv,
)
from app.shared.infrastructure import async_session_factory


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(
        description=(
            "Validate benchmark performance, chain coverage, identity matching, "
            "and DSS weight sensitivity."
        )
    )
    parser.add_argument(
        "--benchmark-csv",
        type=Path,
        help="Aggregate sequential/concurrent CSV. Defaults to the latest thesis benchmark.",
    )
    parser.add_argument(
        "--matching-catalog",
        type=Path,
        default=Path("experiments/matching_catalog.csv"),
    )
    parser.add_argument(
        "--matching-ground-truth",
        type=Path,
        default=Path("experiments/matching_ground_truth.csv"),
    )
    parser.add_argument(
        "--ranking-scenario",
        type=Path,
        default=Path("experiments/ranking_sensitivity_scenario.csv"),
    )
    parser.add_argument("--weight-step", type=Decimal, default=Decimal("0.05"))
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports") / f"experimental_validation_{timestamp}",
    )
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else BACKEND_ROOT / path


def _latest_benchmark() -> Path:
    candidates = sorted(
        (BACKEND_ROOT / "reports").glob("*benchmark*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    aggregate = [
        path
        for path in candidates
        if not path.stem.endswith(("_sources", "_summary"))
    ]
    if not aggregate:
        raise SystemExit("No aggregate benchmark CSV was found in backend/reports.")
    return aggregate[0]


async def main() -> None:
    args = parse_args()
    output_dir = _resolve(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_path = (
        _resolve(args.benchmark_csv) if args.benchmark_csv else _latest_benchmark()
    )

    benchmark_rows, benchmark_summary = analyze_benchmark(benchmark_path)
    coverage_rows = await collect_chain_coverage(async_session_factory)
    matching_details, matching_rows, matching_summary = analyze_matching_quality(
        _resolve(args.matching_catalog),
        _resolve(args.matching_ground_truth),
    )
    sensitivity_details, winner_rows, sensitivity_summary = analyze_weight_sensitivity(
        _resolve(args.ranking_scenario),
        step=args.weight_step,
    )

    write_csv(output_dir / "benchmark_summary.csv", benchmark_rows)
    write_csv(output_dir / "chain_coverage.csv", coverage_rows)
    write_csv(output_dir / "matching_cases.csv", matching_details)
    write_csv(output_dir / "matching_summary.csv", matching_rows)
    write_csv(output_dir / "weight_sensitivity.csv", sensitivity_details)
    write_csv(output_dir / "weight_winner_summary.csv", winner_rows)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": benchmark_summary,
        "matching": matching_summary,
        "weight_sensitivity": sensitivity_summary,
        "chain_coverage_rows": len(coverage_rows),
        "inputs": {
            "benchmark_csv": str(benchmark_path),
            "matching_catalog": str(_resolve(args.matching_catalog)),
            "matching_ground_truth": str(_resolve(args.matching_ground_truth)),
            "ranking_scenario": str(_resolve(args.ranking_scenario)),
        },
    }
    (output_dir / "validation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "report.md").write_text(
        _markdown_report(summary, coverage_rows, winner_rows),
        encoding="utf-8",
    )
    print(f"Experimental validation written to: {output_dir}")
    print(
        "Benchmark reduction: "
        f"{benchmark_summary['duration_reduction_pct']:.1f}% "
        f"(speedup {benchmark_summary['speedup']:.2f}x)"
    )
    print(
        "Matching: "
        f"precision={matching_summary['precision']:.3f}, "
        f"recall={matching_summary['recall']:.3f}, "
        f"F1={matching_summary['f1']:.3f}"
    )
    print(
        "Baseline winner robustness: "
        f"{sensitivity_summary['baseline_winner_robustness_pct']:.1f}%"
    )


def _markdown_report(summary: dict, coverage_rows: list[dict], winner_rows: list[dict]) -> str:
    benchmark = summary["benchmark"]
    matching = summary["matching"]
    sensitivity = summary["weight_sensitivity"]
    lines = [
        "# Validacion experimental",
        "",
        f"Generado: `{summary['generated_at']}`.",
        "",
        "## Rendimiento",
        "",
        f"- Repeticiones emparejadas: {benchmark['iterations']}.",
        f"- Speedup concurrente: {benchmark['speedup']:.3f}x.",
        f"- Reduccion media de duracion: {benchmark['duration_reduction_pct']:.3f}%.",
        f"- Reduccion emparejada media: {benchmark['paired_reduction_mean_pct']:.3f}%.",
        "",
        "## Cobertura por cadena",
        "",
        "| Cadena | Sucursales | Fuentes | Productos publicados | Con precio | ETL aceptado |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in coverage_rows:
        lines.append(
            f"| {row['chain']} | {row['active_branches']} | "
            f"{row['active_scraping_sources']} | {row['published_canonical_products']} | "
            f"{row['products_with_available_price']} | "
            f"{row['etl_acceptance_rate_pct']:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Calidad del matching",
            "",
            f"- Casos etiquetados: {matching['cases']}.",
            f"- Precision: {matching['precision']:.4f}.",
            f"- Recall: {matching['recall']:.4f}.",
            f"- F1: {matching['f1']:.4f}.",
            f"- Accuracy: {matching['accuracy']:.4f}.",
            f"- Abstencion: {matching['abstention_rate_pct']:.3f}%.",
            "",
            "## Sensibilidad de pesos",
            "",
            f"- Escenarios del simplex: {sensitivity['scenarios']}.",
            f"- Ganador base: {sensitivity['baseline_winner']}.",
            f"- Robustez top-1: {sensitivity['baseline_winner_robustness_pct']:.3f}%.",
            f"- Ganadores distintos: {sensitivity['distinct_winners']}.",
            f"- Spearman medio contra baseline: "
            f"{sensitivity['mean_spearman_vs_baseline']:.4f}.",
            "",
            "| Ganador | Escenarios | Participacion |",
            "|---|---:|---:|",
        ]
    )
    for row in winner_rows:
        lines.append(
            f"| {row['winner']} | {row['scenarios_won']} | "
            f"{row['scenario_share_pct']:.3f}% |"
        )
    lines.extend(
        [
            "",
            "Los CSV del directorio conservan los casos y escenarios individuales para auditoria.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    asyncio.run(main())
