"""Use cases for managed scraping source configuration."""

from uuid import UUID, uuid4

from app.modules.ingestion.application.commands import (
    CreateScrapingSourceCommand,
    UpdateScrapingSourceCommand,
)
from app.modules.ingestion.application.dto import ScrapingSourceDTO
from app.modules.ingestion.domain.entities import ScrapingSource
from app.shared.application import UnitOfWorkPort


class CreateScrapingSourceUseCase:
    """Creates a source only for an active supermarket."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: CreateScrapingSourceCommand) -> ScrapingSourceDTO:
        source = ScrapingSource(
            id=uuid4(),
            supermarket_id=command.supermarket_id,
            name=command.name,
            base_url=command.base_url,
            active=command.active,
        )
        async with self._unit_of_work as uow:
            await _require_active_supermarket(uow, source.supermarket_id)
            duplicate = await uow.ingestion.get_source_by_supermarket_and_name(
                source.supermarket_id,
                source.name,
            )
            if duplicate is not None:
                raise ValueError("Scraping source already exists for this supermarket.")
            saved_source = await uow.ingestion.save_source(source)
            await uow.commit()
        return ScrapingSourceDTO.from_entity(saved_source)


class UpdateScrapingSourceUseCase:
    """Updates source configuration without deleting historical runs."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, command: UpdateScrapingSourceCommand) -> ScrapingSourceDTO:
        async with self._unit_of_work as uow:
            source = await uow.ingestion.get_source_by_id(command.source_id)
            if source is None:
                raise ValueError("Scraping source not found.")
            source.update_configuration(
                name=command.name,
                base_url=command.base_url,
                active=command.active,
            )
            duplicate = await uow.ingestion.get_source_by_supermarket_and_name(
                source.supermarket_id,
                source.name,
            )
            if duplicate is not None and duplicate.id != source.id:
                raise ValueError("Scraping source already exists for this supermarket.")
            saved_source = await uow.ingestion.save_source(source)
            await uow.commit()
        return ScrapingSourceDTO.from_entity(saved_source)


class ListScrapingSourcesUseCase:
    """Lists configured sources for administrative views."""

    def __init__(self, unit_of_work: UnitOfWorkPort) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, active_only: bool | None = None) -> list[ScrapingSourceDTO]:
        async with self._unit_of_work as uow:
            sources = await uow.ingestion.list_sources(active_only=active_only)
        return [ScrapingSourceDTO.from_entity(source) for source in sources]


async def _require_active_supermarket(uow: UnitOfWorkPort, supermarket_id: UUID) -> None:
    supermarket = await uow.supermarkets.get_by_id(supermarket_id)
    if supermarket is None or not supermarket.active:
        raise ValueError("Supermarket not found or inactive.")
