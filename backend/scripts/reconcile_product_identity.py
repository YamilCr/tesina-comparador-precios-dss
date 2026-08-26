"""Reports or applies conservative historical canonical-product reconciliation."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

from app.modules.ingestion.application.use_cases.reconcile_product_identity import (
    ProductIdentityReconciliationDTO,
    ReconcileProductIdentityUseCase,
)
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


CSV_FIELDS = (
    "product_source_id",
    "source_name",
    "current_product_id",
    "current_product_name",
    "target_product_id",
    "target_product_name",
    "confidence",
    "method",
)


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(
        description="Reconcile weak source-created products with curated catalog products."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist suggestions. Without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / f"product_identity_reconciliation_{timestamp}.csv",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    result = await ReconcileProductIdentityUseCase(
        SQLAlchemyUnitOfWork(async_session_factory)
    ).execute(apply=args.apply)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(output, result)
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Scanned sources: {result.scanned_sources}")
    print(f"Curated products: {result.curated_products}")
    print(f"Suggestions: {len(result.suggestions)}")
    print(f"Reassigned sources: {result.reassigned_sources}")
    print(f"Deactivated orphan products: {result.deactivated_products}")
    print(f"CSV written to: {output}")


def _write_csv(output: Path, result: ProductIdentityReconciliationDTO) -> None:
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for suggestion in result.suggestions:
            writer.writerow(
                {
                    "product_source_id": suggestion.product_source_id,
                    "source_name": suggestion.source_name,
                    "current_product_id": suggestion.current_product_id,
                    "current_product_name": suggestion.current_product_name,
                    "target_product_id": suggestion.target_product_id,
                    "target_product_name": suggestion.target_product_name,
                    "confidence": suggestion.confidence,
                    "method": suggestion.method,
                }
            )


if __name__ == "__main__":
    asyncio.run(main())
