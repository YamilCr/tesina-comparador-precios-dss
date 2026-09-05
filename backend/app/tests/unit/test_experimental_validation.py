"""Tests for reproducible thesis validation metrics."""

from decimal import Decimal
from pathlib import Path

from app.experiments import (
    analyze_benchmark,
    analyze_matching_quality,
    analyze_weight_sensitivity,
)


EXPERIMENTS = Path(__file__).resolve().parents[3] / "experiments"


def test_matching_ground_truth_reports_conservative_quality_metrics() -> None:
    details, rows, summary = analyze_matching_quality(
        EXPERIMENTS / "matching_catalog.csv",
        EXPERIMENTS / "matching_ground_truth.csv",
    )

    assert len(details) == 36
    assert rows[0]["false_positives"] == 0
    assert summary["precision"] == 1.0
    assert 0.8 < summary["recall"] < 1.0
    assert summary["f1"] > 0.9


def test_weight_sensitivity_sweeps_complete_simplex() -> None:
    details, winners, summary = analyze_weight_sensitivity(
        EXPERIMENTS / "ranking_sensitivity_scenario.csv",
        step=Decimal("0.10"),
    )

    assert len(details) == 66
    assert sum(row["scenarios_won"] for row in winners) == 66
    assert summary["distinct_winners"] == 3
    assert 0 < summary["baseline_winner_robustness_pct"] < 100


def test_benchmark_analysis_uses_paired_repetitions(tmp_path: Path) -> None:
    path = tmp_path / "benchmark.csv"
    path.write_text(
        "iteration,mode,duration_ms,failed_sources,items_scraped\n"
        "1,sequential,1000,0,10\n"
        "1,concurrent,500,0,10\n"
        "2,concurrent,600,0,10\n"
        "2,sequential,1200,0,10\n",
        encoding="utf-8",
    )

    rows, summary = analyze_benchmark(path)

    assert len(rows) == 2
    assert summary["iterations"] == 2
    assert summary["speedup"] == 2.0
    assert summary["duration_reduction_pct"] == 50.0

