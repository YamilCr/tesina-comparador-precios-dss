"""Reports or applies exact multi-supermarket canonical product consolidation."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

from app.modules.ingestion.application.use_cases.consolidate_product_catalog import (
    ProductCatalogConsolidationDTO,
    ConsolidateProductCatalogUseCase,
)
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


CSV_FIELDS = (
    "matching_key",
    "target_product_id",
    "target_product_name",
    "duplicate_product_ids",
    "duplicate_product_names",
    "source_count",
    "supermarket_count",
)


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(
        description=(
            "Consolidate exact product identities observed in multiple supermarkets."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist clusters. Without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / f"product_catalog_consolidation_{timestamp}.csv",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    result = await ConsolidateProductCatalogUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(apply=args.apply)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, result)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Scanned products: {result.scanned_products}")
    print(f"Exact multi-supermarket clusters: {len(result.clusters)}")
    print(f"Reassigned sources: {result.reassigned_sources}")
    print(f"Deactivated duplicate products: {result.deactivated_products}")
    print(f"Enriched canonical products: {result.enriched_products}")
    print(f"CSV written to: {output}")


def _write_csv(output: Path, result: ProductCatalogConsolidationDTO) -> None:
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for cluster in result.clusters:
            writer.writerow(
                {
                    "matching_key": cluster.matching_key,
                    "target_product_id": cluster.target_product_id,
                    "target_product_name": cluster.target_product_name,
                    "duplicate_product_ids": "|".join(
                        str(product_id) for product_id in cluster.duplicate_product_ids
                    ),
                    "duplicate_product_names": "|".join(
                        cluster.duplicate_product_names
                    ),
                    "source_count": cluster.source_count,
                    "supermarket_count": cluster.supermarket_count,
                }
            )


if __name__ == "__main__":
    asyncio.run(main())
