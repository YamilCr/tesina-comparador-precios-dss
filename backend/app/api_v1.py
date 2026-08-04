"""Agregador de routers HTTP v1 del backend DSS."""

from fastapi import APIRouter

from app.modules.basket.interfaces.http import router as basket_router
from app.modules.catalog.interfaces.http import router as catalog_router
from app.modules.decision.interfaces.http import router as decision_router
from app.modules.prices.interfaces.http import router as prices_router
from app.modules.supermarkets.interfaces.http import router as supermarkets_router


router = APIRouter(prefix="/api/v1")
router.include_router(catalog_router)
router.include_router(supermarkets_router)
router.include_router(prices_router)
router.include_router(basket_router)
router.include_router(decision_router)
