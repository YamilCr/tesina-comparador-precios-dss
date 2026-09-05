"""Produces reproducible sequential-versus-concurrent ingestion benchmark data."""

from __future__ import annotations

import argparse
import asyncio
import csv
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean, median, stdev
from uuid import UUID

from app.modules.ingestion.application.dto import ScrapingBenchmarkDTO
from app.modules.ingestion.application.use_cases import BenchmarkScrapingSourcesUseCase
from app.modules.ingestion.domain.entities import ScrapingSource
from app.modules.ingestion.domain.ports import ScraperPort
from app.modules.ingestion.infrastructure.scrapers import create_scraper_for_source
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


CSV_FIELDS = (
    "recorded_at",
    "iteration",
    "mode",
    "execution_order",
    "source_count",
    "source_ids",
    "queries",
    "city",
    "result_limit",
    "max_concurrency",
    "timeout_seconds",
    "duration_ms",
    "throughput_items_per_second",
    "successful_sources",
    "failed_sources",
    "items_scraped",
    "items_loaded",
    "items_rejected",
    "items_duplicates",
    "items_unmatched",
    "run_ids",
    "errors",
)

SOURCE_CSV_FIELDS = (
    "recorded_at",
    "iteration",
    "mode",
    "execution_order",
    "source_id",
    "source_name",
    "duration_ms",
    "status",
    "items_scraped",
    "items_loaded",
    "items_rejected",
    "items_duplicates",
    "items_unmatched",
    "run_id",
    "error",
)

SUMMARY_CSV_FIELDS = (
    "scope",
    "mode",
    "source_id",
    "source_name",
    "samples",
    "success_rate_pct",
    "mean_duration_ms",
    "median_duration_ms",
    "stdev_duration_ms",
    "p95_duration_ms",
    "min_duration_ms",
    "max_duration_ms",
    "mean_items_scraped",
    "mean_items_loaded",
    "mean_throughput_items_per_second",
    "speedup_vs_sequential",
    "duration_reduction_pct",
)


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(
        description="Measure the same production ingestion flow sequentially and concurrently."
    )
    parser.add_argument("--source-id", action="append", required=True, type=UUID)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--city", default="Comodoro Rivadavia")
    parser.add_argument("--limit", type=int, default=5, choices=range(1, 21))
    parser.add_argument("--repetitions", type=int, default=3, choices=range(1, 21))
    parser.add_argument("--warmups", type=int, default=1, choices=range(0, 6))
    parser.add_argument("--max-concurrency", type=int, default=2, choices=range(1, 6))
    parser.add_argument("--timeout-seconds", type=int, default=20, choices=range(1, 61))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / f"scraping_concurrency_{timestamp}.csv",
        help="CSV path relative to backend/ unless an absolute path is supplied.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    source_ids = list(dict.fromkeys(args.source_id))
    if len(source_ids) < 2:
        raise SystemExit("A concurrency benchmark requires at least two different --source-id values.")

    def create_scraper(source: ScrapingSource) -> ScraperPort:
        return create_scraper_for_source(
            source,
            queries=args.query,
            city=args.city,
            result_limit=args.limit,
        )

    benchmark = BenchmarkScrapingSourcesUseCase(
        SQLAlchemyUnitOfWork(async_session_factory),
        create_scraper,
        max_concurrency=args.max_concurrency,
        timeout_seconds=args.timeout_seconds,
    )
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str | int]] = []
    source_records: list[dict[str, str | int | float]] = []

    for _ in range(args.warmups):
        for mode in ("sequential", "concurrent"):
            await benchmark.execute(source_ids, mode=mode)

    for iteration in range(1, args.repetitions + 1):
        modes = ("sequential", "concurrent") if iteration % 2 else ("concurrent", "sequential")
        for position, mode in enumerate(modes, start=1):
            result = await benchmark.execute(source_ids, mode=mode)
            recorded_at = datetime.now(timezone.utc).isoformat()
            records.append(
                _record(
                    result,
                    recorded_at=recorded_at,
                    iteration=iteration,
                    execution_order=position,
                    source_ids=source_ids,
                    queries=args.query,
                    city=args.city,
                    result_limit=args.limit,
                    max_concurrency=args.max_concurrency,
                    timeout_seconds=args.timeout_seconds,
                )
            )
            source_records.extend(
                _source_records(
                    result,
                    recorded_at=recorded_at,
                    iteration=iteration,
                    execution_order=position,
                )
            )

    _write_csv(output_path, records)
    source_output_path = output_path.with_name(f"{output_path.stem}_sources.csv")
    summary_output_path = output_path.with_name(f"{output_path.stem}_summary.csv")
    _write_rows(source_output_path, SOURCE_CSV_FIELDS, source_records)
    _write_rows(
        summary_output_path,
        SUMMARY_CSV_FIELDS,
        _summary_records(records, source_records),
    )
    _print_summary(records, output_path, source_output_path, summary_output_path)


def _record(
    result: ScrapingBenchmarkDTO,
    *,
    recorded_at: str,
    iteration: int,
    execution_order: int,
    source_ids: list[UUID],
    queries: list[str],
    city: str,
    result_limit: int,
    max_concurrency: int,
    timeout_seconds: int,
) -> dict[str, str | int]:
    successful = [
        source
        for source in result.sources
        if source.error_message is None and source.run is not None and source.run.status == "succeeded"
    ]
    loads = [source.load for source in result.sources if source.load is not None]
    return {
        "recorded_at": recorded_at,
        "iteration": iteration,
        "mode": result.mode,
        "execution_order": execution_order,
        "source_count": len(result.sources),
        "source_ids": ";".join(str(source_id) for source_id in source_ids),
        "queries": ";".join(query.strip() for query in queries),
        "city": city,
        "result_limit": result_limit,
        "max_concurrency": max_concurrency,
        "timeout_seconds": timeout_seconds,
        "duration_ms": result.duration_ms,
        "throughput_items_per_second": round(
            sum(source.run.items_scraped for source in result.sources if source.run)
            / max(result.duration_ms / 1000, 0.001),
            3,
        ),
        "successful_sources": len(successful),
        "failed_sources": len(result.sources) - len(successful),
        "items_scraped": sum(source.run.items_scraped for source in result.sources if source.run),
        "items_loaded": sum(load.loaded for load in loads),
        "items_rejected": sum(load.rejected for load in loads),
        "items_duplicates": sum(load.duplicates for load in loads),
        "items_unmatched": sum(load.unmatched for load in loads),
        "run_ids": ";".join(str(source.run.id) for source in result.sources if source.run),
        "errors": " | ".join(
            f"{source.source_name}: {source.error_message}"
            for source in result.sources
            if source.error_message
        ),
    }


def _source_records(
    result: ScrapingBenchmarkDTO,
    *,
    recorded_at: str,
    iteration: int,
    execution_order: int,
) -> list[dict[str, str | int | float]]:
    records = []
    for source in result.sources:
        load = source.load
        run = source.run
        records.append(
            {
                "recorded_at": recorded_at,
                "iteration": iteration,
                "mode": result.mode,
                "execution_order": execution_order,
                "source_id": str(source.source_id),
                "source_name": source.source_name,
                "duration_ms": source.duration_ms or 0,
                "status": run.status if run is not None else "failed",
                "items_scraped": run.items_scraped if run is not None else 0,
                "items_loaded": load.loaded if load is not None else 0,
                "items_rejected": load.rejected if load is not None else 0,
                "items_duplicates": load.duplicates if load is not None else 0,
                "items_unmatched": load.unmatched if load is not None else 0,
                "run_id": str(run.id) if run is not None else "",
                "error": source.error_message or "",
            }
        )
    return records


def _write_csv(output_path: Path, records: list[dict[str, str | int]]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def _write_rows(
    output_path: Path,
    fields: tuple[str, ...],
    records: list[dict],
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def _summary_records(
    records: list[dict[str, str | int]],
    source_records: list[dict[str, str | int | float]],
) -> list[dict[str, str | int | float]]:
    overall = {
        mode: [record for record in records if record["mode"] == mode]
        for mode in ("sequential", "concurrent")
    }
    sequential_mean = fmean(float(row["duration_ms"]) for row in overall["sequential"])
    concurrent_mean = fmean(float(row["duration_ms"]) for row in overall["concurrent"])
    speedup = sequential_mean / concurrent_mean if concurrent_mean else 0
    reduction = (
        ((sequential_mean - concurrent_mean) / sequential_mean) * 100
        if sequential_mean
        else 0
    )
    summaries = []
    for mode, rows in overall.items():
        summaries.append(
            _summary_row(
                scope="overall",
                mode=mode,
                source_id="",
                source_name="",
                rows=rows,
                speedup=speedup,
                reduction=reduction,
            )
        )

    source_keys = sorted(
        {(str(row["source_id"]), str(row["source_name"])) for row in source_records}
    )
    for source_id, source_name in source_keys:
        rows_by_mode = {
            mode: [
                row
                for row in source_records
                if row["source_id"] == source_id and row["mode"] == mode
            ]
            for mode in ("sequential", "concurrent")
        }
        sequential_source_mean = fmean(
            float(row["duration_ms"]) for row in rows_by_mode["sequential"]
        )
        concurrent_source_mean = fmean(
            float(row["duration_ms"]) for row in rows_by_mode["concurrent"]
        )
        source_speedup = (
            sequential_source_mean / concurrent_source_mean
            if concurrent_source_mean
            else 0
        )
        source_reduction = (
            (
                (sequential_source_mean - concurrent_source_mean)
                / sequential_source_mean
            )
            * 100
            if sequential_source_mean
            else 0
        )
        for mode in ("sequential", "concurrent"):
            rows = rows_by_mode[mode]
            if rows:
                summaries.append(
                    _summary_row(
                        scope="source",
                        mode=mode,
                        source_id=source_id,
                        source_name=source_name,
                        rows=rows,
                        speedup=source_speedup,
                        reduction=source_reduction,
                    )
                )
    return summaries


def _summary_row(
    *,
    scope: str,
    mode: str,
    source_id: str,
    source_name: str,
    rows: list[dict],
    speedup: float = 0,
    reduction: float = 0,
) -> dict[str, str | int | float]:
    durations = [float(row["duration_ms"]) for row in rows]
    scraped = [float(row["items_scraped"]) for row in rows]
    loaded = [float(row["items_loaded"]) for row in rows]
    throughputs = [
        item_count / max(duration / 1000, 0.001)
        for item_count, duration in zip(scraped, durations, strict=True)
    ]
    successful = sum(
        1
        for row in rows
        if (
            row.get("failed_sources", 0) == 0
            if scope == "overall"
            else row.get("status") == "succeeded"
        )
    )
    ordered = sorted(durations)
    p95_index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "scope": scope,
        "mode": mode,
        "source_id": source_id,
        "source_name": source_name,
        "samples": len(rows),
        "success_rate_pct": round((successful / len(rows)) * 100, 3),
        "mean_duration_ms": round(fmean(durations), 3),
        "median_duration_ms": round(median(durations), 3),
        "stdev_duration_ms": round(stdev(durations), 3) if len(durations) > 1 else 0,
        "p95_duration_ms": round(ordered[p95_index], 3),
        "min_duration_ms": round(min(durations), 3),
        "max_duration_ms": round(max(durations), 3),
        "mean_items_scraped": round(fmean(scraped), 3),
        "mean_items_loaded": round(fmean(loaded), 3),
        "mean_throughput_items_per_second": round(fmean(throughputs), 3),
        "speedup_vs_sequential": round(speedup, 4),
        "duration_reduction_pct": round(reduction, 3),
    }


def _print_summary(
    records: list[dict[str, str | int]],
    output_path: Path,
    source_output_path: Path,
    summary_output_path: Path,
) -> None:
    durations = {
        mode: [int(record["duration_ms"]) for record in records if record["mode"] == mode]
        for mode in ("sequential", "concurrent")
    }
    sequential_mean = fmean(durations["sequential"])
    concurrent_mean = fmean(durations["concurrent"])
    improvement = ((sequential_mean - concurrent_mean) / sequential_mean) * 100
    print(f"CSV written to: {output_path}")
    print(f"Source detail CSV written to: {source_output_path}")
    print(f"Statistical summary CSV written to: {summary_output_path}")
    print(f"Sequential mean: {sequential_mean:.1f} ms")
    print(f"Concurrent mean: {concurrent_mean:.1f} ms")
    print(f"Observed reduction: {improvement:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
