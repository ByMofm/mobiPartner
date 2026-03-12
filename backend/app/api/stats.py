from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.property import Property, PropertyListing
from app.models.enums import ListingType
from app.schemas.property import StatsOverview

router = APIRouter()


@router.get("/overview", response_model=StatsOverview)
def stats_overview(db: Session = Depends(get_db)):
    total = db.query(func.count(Property.id)).scalar() or 0
    active = db.query(func.count(Property.id)).filter(Property.is_active == True).scalar() or 0

    avg_sale = (
        db.query(func.avg(Property.current_price_usd))
        .filter(Property.listing_type == ListingType.SALE, Property.current_price_usd.isnot(None))
        .scalar()
    )
    avg_rent = (
        db.query(func.avg(Property.current_price_usd))
        .filter(Property.listing_type == ListingType.RENT, Property.current_price_usd.isnot(None))
        .scalar()
    )

    total_listings = db.query(func.count(PropertyListing.id)).scalar() or 0

    source_counts = (
        db.query(PropertyListing.source, func.count(PropertyListing.id))
        .group_by(PropertyListing.source)
        .all()
    )
    sources = {str(s.value if hasattr(s, "value") else s): c for s, c in source_counts}

    without_coords = (
        db.query(func.count(Property.id))
        .filter(Property.is_active == True, Property.latitude.is_(None))
        .scalar() or 0
    )

    return StatsOverview(
        total_properties=total,
        active_properties=active,
        avg_price_usd_sale=round(avg_sale, 2) if avg_sale else None,
        avg_price_usd_rent=round(avg_rent, 2) if avg_rent else None,
        total_listings=total_listings,
        sources=sources,
        without_coords=without_coords,
    )
