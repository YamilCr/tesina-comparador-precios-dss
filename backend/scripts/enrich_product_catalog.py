"""Reports or applies catalog enrichment from loaded staging evidence."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

from app.modules.ingestion.application.use_cases.enrich_product_catalog import (
    ProductCatalogEnrichmentDTO,
    EnrichProductCatalogUseCase,
)
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


CSV_FIELDS = (
    "record_type",
    "product_id",
    "product_name",
    "product_source_id",
    "product_source_ids",
    "brand_name",
    "creates_brand",
    "gtin",
    "evidence_rows",
    "evidence_sources",
    "reason",
)


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(
        description="Enrich product brands and GTIN from consistent staging evidence."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist safe suggestions. Without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / f"product_catalog_enrichment_{timestamp}.csv",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    result = await EnrichProductCatalogUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(apply=args.apply)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, result)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Loaded evidence rows: {result.evidence_rows}")
    print(f"Brand suggestions: {len(result.brand_suggestions)}")
    print(f"GTIN suggestions: {len(result.gtin_suggestions)}")
    print(f"GTIN conflicts: {len(result.gtin_conflicts)}")
    print(f"Created brands: {result.created_brands}")
    print(f"Enriched products: {result.enriched_products}")
    print(f"Enriched publications: {result.enriched_product_sources}")
    print(f"CSV written to: {output}")


def _write_csv(output: Path, result: ProductCatalogEnrichmentDTO) -> None:
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for suggestion in result.brand_suggestions:
            writer.writerow(
                {
                    "record_type": "brand",
                    "product_id": suggestion.product_id,
                    "product_name": suggestion.product_name,
                    "brand_name": suggestion.brand_name,
                    "creates_brand": suggestion.creates_brand,
                    "evidence_rows": suggestion.evidence_rows,
                    "evidence_sources": suggestion.evidence_sources,
                }
            )
        for suggestion in result.gtin_suggestions:
            writer.writerow(
                {
                    "record_type": "gtin",
                    "product_id": suggestion.product_id,
                    "product_name": suggestion.source_name,
                    "product_source_id": suggestion.product_source_id,
                    "gtin": suggestion.gtin,
                    "evidence_rows": suggestion.evidence_rows,
                }
            )
        for conflict in result.gtin_conflicts:
            writer.writerow(
                {
                    "record_type": "gtin_conflict",
                    "product_id": "|".join(str(value) for value in conflict.product_ids),
                    "product_source_ids": "|".join(
                        str(value) for value in conflict.product_source_ids
                    ),
                    "gtin": conflict.gtin,
                    "reason": conflict.reason,
                }
            )


if __name__ == "__main__":
    asyncio.run(main())
