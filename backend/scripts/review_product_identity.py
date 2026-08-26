"""Scans and decides assisted canonical product identity reviews."""

from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.modules.ingestion.application.use_cases import (
    DecideProductIdentityReviewUseCase,
    GenerateProductIdentityReviewsUseCase,
)
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


def parse_args() -> argparse.Namespace:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    parser = argparse.ArgumentParser(description="Manage assisted product identity reviews.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan", help="Generate new pending review candidates.")
    scan.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / f"product_identity_reviews_{timestamp}.csv",
    )
    listing = subparsers.add_parser("list", help="List persisted reviews.")
    listing.add_argument(
        "--status",
        choices=("pending", "approved", "rejected"),
        default="pending",
    )
    for decision in ("approve", "reject"):
        command = subparsers.add_parser(decision, help=f"{decision.title()} one review.")
        command.add_argument("--review-id", type=UUID, required=True)
        command.add_argument("--note", required=True)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if args.command == "scan":
        result = await GenerateProductIdentityReviewsUseCase(_uow()).execute()
        rows = await _review_rows("pending")
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        _write_csv(output, rows)
        print(f"Generated: {result.generated}")
        print(f"GTIN candidates: {result.gtin_candidates}")
        print(f"Semantic candidates: {result.semantic_candidates}")
        print(f"Pending reviews: {result.pending}")
        print(f"CSV written to: {output}")
        return
    if args.command == "list":
        rows = await _review_rows(args.status)
        for row in rows:
            print(
                f"{row['id']} | {row['review_type']} | {row['status']} | "
                f"{row['source_product_name']} -> {row['target_product_name']} | "
                f"evidence={row['evidence_value']}"
            )
        print(f"Reviews: {len(rows)}")
        return

    result = await DecideProductIdentityReviewUseCase(_uow()).execute(
        args.review_id,
        decision=args.command,
        note=args.note,
    )
    print(f"Review: {result.review.id}")
    print(f"Status: {result.review.status}")
    print(f"Reassigned publications: {result.reassigned_sources}")
    print(f"Deactivated source product: {result.deactivated_product}")


def _uow() -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(async_session_factory)


async def _review_rows(status: str) -> list[dict]:
    uow = _uow()
    async with uow as active_uow:
        reviews = await active_uow.ingestion.list_identity_reviews(status=status)
        rows = []
        for review in reviews:
            source = await active_uow.products.get_by_id(review.source_product_id)
            target = await active_uow.products.get_by_id(review.target_product_id)
            rows.append(
                {
                    "id": review.id,
                    "review_type": review.review_type,
                    "status": review.status,
                    "source_product_id": review.source_product_id,
                    "source_product_name": source.normalized_name if source else "<missing>",
                    "target_product_id": review.target_product_id,
                    "target_product_name": target.normalized_name if target else "<missing>",
                    "evidence_value": review.evidence_value,
                    "confidence": review.confidence,
                    "rationale": review.rationale,
                    "decision_note": review.decision_note or "",
                }
            )
    return rows


def _write_csv(output: Path, rows: list[dict]) -> None:
    fields = tuple(rows[0]) if rows else (
        "id",
        "review_type",
        "status",
        "source_product_id",
        "source_product_name",
        "target_product_id",
        "target_product_name",
        "evidence_value",
        "confidence",
        "rationale",
        "decision_note",
    )
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    asyncio.run(main())
