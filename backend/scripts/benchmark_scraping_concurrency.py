"""Produces reproducible sequential-versus-concurrent ingestion benchmark data."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean
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

    for _ in range(args.warmups):
        for mode in ("sequential", "concurrent"):
            await benchmark.execute(source_ids, mode=mode)

    for iteration in range(1, args.repetitions + 1):
        modes = ("sequential", "concurrent") if iteration % 2 else ("concurrent", "sequential")
        for position, mode in enumerate(modes, start=1):
            result = await benchmark.execute(source_ids, mode=mode)
            records.append(
                _record(
                    result,
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

    _write_csv(output_path, records)
    _print_summary(records, output_path)


def _record(
    result: ScrapingBenchmarkDTO,
    *,
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
        "recorded_at": datetime.now(timezone.utc).isoformat(),
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


def _write_csv(output_path: Path, records: list[dict[str, str | int]]) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def _print_summary(records: list[dict[str, str | int]], output_path: Path) -> None:
    durations = {
        mode: [int(record["duration_ms"]) for record in records if record["mode"] == mode]
        for mode in ("sequential", "concurrent")
    }
    sequential_mean = fmean(durations["sequential"])
    concurrent_mean = fmean(durations["concurrent"])
    improvement = ((sequential_mean - concurrent_mean) / sequential_mean) * 100
    print(f"CSV written to: {output_path}")
    print(f"Sequential mean: {sequential_mean:.1f} ms")
    print(f"Concurrent mean: {concurrent_mean:.1f} ms")
    print(f"Observed reduction: {improvement:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
