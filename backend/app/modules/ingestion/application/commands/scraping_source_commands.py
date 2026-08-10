"""Commands for administrating scraping source configuration."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CreateScrapingSourceCommand:
    supermarket_id: UUID
    name: str
    base_url: str
    branch_id: UUID | None = None
    active: bool = True


@dataclass(frozen=True)
class UpdateScrapingSourceCommand:
    source_id: UUID
    name: str | None = None
    base_url: str | None = None
    branch_id: UUID | None = None
    active: bool | None = None

    def __post_init__(self) -> None:
        if (
            self.name is None
            and self.base_url is None
            and self.branch_id is None
            and self.active is None
        ):
            raise ValueError("Scraping source update requires at least one field.")
