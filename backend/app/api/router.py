from fastapi import APIRouter, Depends

from app.api.properties import router as properties_router
from app.api.locations import router as locations_router
from app.api.stats import router as stats_router
from app.api.scrape import router as scrape_router
from app.middleware.auth import verify_api_key, verify_admin_key

api_router = APIRouter(dependencies=[Depends(verify_api_key)])

api_router.include_router(properties_router, prefix="/properties", tags=["properties"])
api_router.include_router(locations_router, prefix="/locations", tags=["locations"])
api_router.include_router(stats_router, prefix="/stats", tags=["stats"])
api_router.include_router(
    scrape_router,
    prefix="/scrape",
    tags=["scrape"],
    dependencies=[Depends(verify_admin_key)],
)
