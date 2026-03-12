from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, case
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.location import Location
from app.models.property import Property, PropertyListing, PriceHistory
from app.models.enums import PropertyType, ListingType
from app.schemas.property import (
    PropertyListItem,
    PropertyListResponse,
    PropertyDetail,
    PropertyMapItem,
    PriceContextSchema,
    ImageAnalysisSchema,
)
from app.services.pricing import get_price_context

router = APIRouter()


def _get_thumbnail(db: Session, property_id: int) -> str | None:
    """Get the first image URL from the first active listing with images."""
    listing = (
        db.query(PropertyListing)
        .filter(
            PropertyListing.property_id == property_id,
            PropertyListing.is_active == True,
            func.array_length(PropertyListing.image_urls, 1) > 0,
        )
        .first()
    )
    if listing and listing.image_urls:
        return listing.image_urls[0]
    return None


def _enrich_list_items(db: Session, properties: list) -> list[PropertyListItem]:
    """Convert Property ORM objects to PropertyListItem with thumbnails."""
    if not properties:
        return []

    prop_ids = [p.id for p in properties]

    # Batch fetch first image for each property
    from sqlalchemy import distinct
    thumbnail_map: dict[int, str] = {}
    listings = (
        db.query(PropertyListing.property_id, PropertyListing.image_urls)
        .filter(
            PropertyListing.property_id.in_(prop_ids),
            PropertyListing.is_active == True,
            func.array_length(PropertyListing.image_urls, 1) > 0,
        )
        .all()
    )
    for pid, imgs in listings:
        if pid not in thumbnail_map and imgs:
            thumbnail_map[pid] = imgs[0]

    items = []
    for p in properties:
        item = PropertyListItem.model_validate(p)
        item.thumbnail_url = thumbnail_map.get(p.id)
        items.append(item)
    return items


@router.get("/by-ids", response_model=PropertyListResponse)
def get_properties_by_ids(
    ids: str = Query(..., description="Comma-separated property IDs (max 50)"),
    db: Session = Depends(get_db),
):
    id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()][:50]
    if not id_list:
        return PropertyListResponse(items=[], total=0, page=1, page_size=len(id_list))

    properties = db.query(Property).filter(Property.id.in_(id_list)).all()
    items = _enrich_list_items(db, properties)
    return PropertyListResponse(items=items, total=len(items), page=1, page_size=len(items))


@router.get("", response_model=PropertyListResponse)
def list_properties(
    property_type: list[PropertyType] | None = Query(None),
    listing_type: ListingType | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    location_id: int | None = None,
    bedrooms: int | None = None,
    apto_credito: bool | None = None,
    min_zone_score: int | None = None,
    order_by: str = Query("score_desc", description="score_desc|price_asc|price_desc|newest"),
    bbox: str | None = Query(None, description="min_lat,min_lng,max_lat,max_lng"),
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Property).filter(Property.is_active == is_active)

    if property_type:
        query = query.filter(Property.property_type.in_(property_type))
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    if min_price is not None:
        query = query.filter(Property.current_price_usd >= min_price)
    if max_price is not None:
        query = query.filter(Property.current_price_usd <= max_price)
    if min_area is not None:
        query = query.filter(Property.total_area_m2 >= min_area)
    if max_area is not None:
        query = query.filter(Property.total_area_m2 <= max_area)
    if location_id is not None:
        # Include the selected location and all its descendants
        all_locs = db.query(Location).all()
        loc_map: dict[int | None, list[int]] = {}
        for loc in all_locs:
            loc_map.setdefault(loc.parent_id, []).append(loc.id)

        def collect_ids(root_id: int) -> list[int]:
            ids = [root_id]
            for child_id in loc_map.get(root_id, []):
                ids.extend(collect_ids(child_id))
            return ids

        location_ids = collect_ids(location_id)
        query = query.filter(Property.location_id.in_(location_ids))
    if bedrooms is not None:
        query = query.filter(Property.bedrooms >= bedrooms)
    if apto_credito:
        query = query.filter(Property.apto_credito == True)
    if min_zone_score is not None:
        query = query.filter(Property.zone_score >= min_zone_score)
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) == 4:
            min_lat, min_lng, max_lat, max_lng = parts
            query = query.filter(
                Property.latitude >= min_lat,
                Property.latitude <= max_lat,
                Property.longitude >= min_lng,
                Property.longitude <= max_lng,
            )

    total = query.count()

    if order_by == "score_desc":
        # Use overall_score if available, fallback to price_score
        has_price = case((func.coalesce(Property.current_price_usd, 0) > 0, 0), else_=1)
        order_clauses = [
            has_price.asc(),
            func.coalesce(Property.overall_score, Property.price_score, -1).desc(),
            Property.last_seen_at.desc(),
        ]
    elif order_by == "price_asc":
        has_price = case((Property.current_price_usd.isnot(None), 0), else_=1)
        order_clauses = [has_price.asc(), Property.current_price_usd.asc()]
    elif order_by == "price_desc":
        order_clauses = [Property.current_price_usd.desc().nulls_last()]
    else:
        order_clauses = [Property.last_seen_at.desc()]

    properties = (
        query.order_by(*order_clauses)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = _enrich_list_items(db, properties)

    return PropertyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/map", response_model=list[PropertyMapItem])
def map_properties(
    property_type: PropertyType | None = None,
    listing_type: ListingType | None = None,
    bbox: str | None = Query(None, description="min_lat,min_lng,max_lat,max_lng"),
    db: Session = Depends(get_db),
):
    query = db.query(Property).filter(
        Property.is_active == True,
        Property.latitude.isnot(None),
        Property.longitude.isnot(None),
    )

    if property_type:
        query = query.filter(Property.property_type == property_type)
    if listing_type:
        query = query.filter(Property.listing_type == listing_type)
    if bbox:
        parts = [float(x) for x in bbox.split(",")]
        if len(parts) == 4:
            min_lat, min_lng, max_lat, max_lng = parts
            query = query.filter(
                Property.latitude >= min_lat,
                Property.latitude <= max_lat,
                Property.longitude >= min_lng,
                Property.longitude <= max_lng,
            )

    properties = query.limit(5000).all()

    # Batch fetch thumbnails for map items
    prop_ids = [p.id for p in properties]
    thumbnail_map: dict[int, str] = {}
    if prop_ids:
        listings = (
            db.query(PropertyListing.property_id, PropertyListing.image_urls)
            .filter(
                PropertyListing.property_id.in_(prop_ids),
                PropertyListing.is_active == True,
                func.array_length(PropertyListing.image_urls, 1) > 0,
            )
            .all()
        )
        for pid, imgs in listings:
            if pid not in thumbnail_map and imgs:
                thumbnail_map[pid] = imgs[0]

    items = []
    for p in properties:
        item = PropertyMapItem.model_validate(p)
        item.thumbnail_url = thumbnail_map.get(p.id)
        items.append(item)
    return items


@router.get("/{property_id}/similar", response_model=list[PropertyListItem])
def get_similar_properties(
    property_id: int,
    db: Session = Depends(get_db),
):
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    query = db.query(Property).filter(
        Property.id != property_id,
        Property.is_active == True,
        Property.property_type == prop.property_type,
        Property.listing_type == prop.listing_type,
    )

    # Price range +-30%
    if prop.current_price_usd:
        low = prop.current_price_usd * 0.7
        high = prop.current_price_usd * 1.3
        query = query.filter(
            Property.current_price_usd >= low,
            Property.current_price_usd <= high,
        )

    # Order by geographic proximity if coords available
    if prop.latitude and prop.longitude:
        distance = func.pow(Property.latitude - prop.latitude, 2) + func.pow(Property.longitude - prop.longitude, 2)
        query = query.filter(
            Property.latitude.isnot(None),
            Property.longitude.isnot(None),
        ).order_by(distance.asc())
    else:
        query = query.order_by(Property.last_seen_at.desc())

    properties = query.limit(6).all()
    return _enrich_list_items(db, properties)


@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(property_id: int, db: Session = Depends(get_db)):
    prop = (
        db.query(Property)
        .options(
            joinedload(Property.listings),
            joinedload(Property.price_history),
            joinedload(Property.image_analysis),
        )
        .filter(Property.id == property_id)
        .first()
    )
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    detail = PropertyDetail.model_validate(prop)
    # Set thumbnail from first listing with images
    for listing in prop.listings:
        if listing.image_urls:
            detail.thumbnail_url = listing.image_urls[0]
            break
    ctx = get_price_context(db, property_id)
    if ctx:
        detail.price_context = PriceContextSchema(**ctx)
    # Image analysis
    if prop.image_analysis:
        ia = prop.image_analysis[0] if isinstance(prop.image_analysis, list) else prop.image_analysis
        detail.image_analysis = ImageAnalysisSchema.model_validate(ia)
    return detail
