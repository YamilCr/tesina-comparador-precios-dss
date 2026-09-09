"""Recover missing image links from previously loaded scraper payloads."""

import asyncio

from sqlalchemy import select

from app.modules.catalog.infrastructure.persistence import ProductModel, ProductSourceModel
from app.modules.ingestion.application.product_images import normalize_image_url
from app.modules.ingestion.infrastructure.persistence.sqlalchemy_models import ScrapedProductModel
from app.shared.infrastructure import async_session_factory


async def backfill(session) -> tuple[int, int]:
    rows = await session.execute(
        select(ScrapedProductModel, ProductSourceModel, ProductModel)
        .join(ProductSourceModel, ScrapedProductModel.producto_fuente_id == ProductSourceModel.id)
        .join(ProductModel, ProductSourceModel.producto_id == ProductModel.id)
        .where(ScrapedProductModel.estado == "loaded", ProductSourceModel.activo.is_(True))
        .order_by(ScrapedProductModel.created_at.desc(), ScrapedProductModel.id)
    )
    sources_updated = products_updated = 0
    for staged, source, product in rows:
        url = normalize_image_url(staged.payload_crudo.get("image_url"), staged.url_producto)
        if not source.image_url and url:
            source.image_url = url
            sources_updated += 1
        if not product.image_url and source.image_url:
            product.image_url = source.image_url
            products_updated += 1
    await session.flush()
    return sources_updated, products_updated


async def main() -> None:
    async with async_session_factory() as session:
        sources, products = await backfill(session)
        await session.commit()
    print(f"Image links recovered: {sources} publications, {products} products.")


if __name__ == "__main__":
    asyncio.run(main())
