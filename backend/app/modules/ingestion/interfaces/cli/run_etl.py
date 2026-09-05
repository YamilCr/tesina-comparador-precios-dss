"""Manual CLI to validate and load one staged scraping run."""

import argparse
import asyncio
import json
from dataclasses import asdict
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.dependencies import get_product_search_index
from app.modules.ingestion.application.use_cases import LoadScrapingRunUseCase
from app.shared.infrastructure import SQLAlchemyUnitOfWork, async_session_factory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and load one scraping run into price history.")
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument(
        "--branch-id",
        type=UUID,
        help="Optional override. Defaults to the target branch configured for the scraping source.",
    )
    parser.add_argument(
        "--no-create-products",
        action="store_true",
        help="Leave exact-match failures as unmatched instead of creating catalog products.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    use_case = LoadScrapingRunUseCase(
        SQLAlchemyUnitOfWork(async_session_factory),
        get_product_search_index(),
    )
    try:
        result = await use_case.execute(
            args.run_id,
            args.branch_id,
            create_missing_products=not args.no_create_products,
        )
    except OperationalError as error:
        if "no such table: producto_extraido" not in str(error):
            raise
        raise SystemExit(
            "The configured database has not applied the ETL migration. "
            "Run `uv run alembic upgrade head` using the same DATABASE_URL."
        ) from error
    print(json.dumps(asdict(result), default=str, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
