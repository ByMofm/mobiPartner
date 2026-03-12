import logging

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.property import Property, PriceHistory
from app.models.enums import CurrencyType
from app.utils.currency import convert_to_usd

logger = logging.getLogger(__name__)


def compute_all_scores(db: Session, usd_ars_rate: float) -> dict:
    """Orchestrator: backfill USD prices, invalidate bad ones, then compute scores."""
    backfilled = _backfill_usd_prices(db, usd_ars_rate)
    db.flush()  # ensure backfilled values are visible to the next query
    invalidated = _invalidate_bad_prices(db)
    db.flush()  # ensure invalidated NULLs are visible before scoring
    scored = _score_properties(db)
    db.commit()
    return {
        "properties_backfilled": backfilled,
        "properties_invalidated": invalidated,
        "properties_scored": scored,
        "usd_ars_rate": usd_ars_rate,
    }


def _backfill_usd_prices(db: Session, rate: float) -> int:
    """Fill current_price_usd and price_per_m2_usd for properties missing them."""
    props = (
        db.query(Property)
        .filter(
            Property.is_active == True,
            Property.current_price.isnot(None),
            Property.current_currency.isnot(None),
            Property.current_price_usd.is_(None),
        )
        .all()
    )

    count = 0
    for prop in props:
        price_usd = convert_to_usd(prop.current_price, prop.current_currency.value, rate)
        if price_usd is not None:
            prop.current_price_usd = price_usd
            if prop.total_area_m2 and prop.total_area_m2 > 0:
                prop.price_per_m2_usd = round(price_usd / prop.total_area_m2, 2)
            count += 1

    # Also backfill PriceHistory.price_usd
    histories = (
        db.query(PriceHistory)
        .filter(PriceHistory.price_usd.is_(None))
        .all()
    )
    for ph in histories:
        ph.price_usd = convert_to_usd(ph.price, ph.currency.value, rate)
        ph.usd_ars_rate = rate

    logger.info(f"Backfilled {count} properties, {len(histories)} price_history records")
    return count


# Minimum valid USD price per listing type — below these values are considered data errors
MIN_VALID_PRICE_USD = {
    "sale": 500.0,          # Nothing in Tucumán sells for under USD 500
    "rent": 10.0,           # Nothing rents for under USD 10/month
    "temporary_rent": 5.0,  # Nothing rents temporarily for under USD 5
}


def _invalidate_bad_prices(db: Session) -> int:
    """Null out current_price_usd for properties with clearly wrong USD values."""
    props = (
        db.query(Property)
        .filter(
            Property.is_active == True,
            Property.current_price_usd.isnot(None),
        )
        .all()
    )

    invalidated = 0
    for p in props:
        min_price = MIN_VALID_PRICE_USD.get(p.listing_type.value, 0)
        if p.current_price_usd < min_price:
            p.current_price_usd = None
            p.price_per_m2_usd = None
            p.price_score = None
            invalidated += 1

    logger.info(f"Invalidated {invalidated} properties with bad USD prices")
    return invalidated


def _score_properties(db: Session) -> int:
    """Score properties by current_price_usd percentile within their group.

    Groups by (property_type, listing_type). Min 5 comparables required.
    Only properties with valid prices (above MIN_VALID_PRICE_USD) are scored.
    """
    props = (
        db.query(Property)
        .filter(
            Property.is_active == True,
            Property.current_price_usd.isnot(None),
        )
        .all()
    )

    # Group by (property_type, listing_type), only valid prices
    groups: dict[tuple, list[Property]] = {}
    invalid_props = []
    for p in props:
        min_price = MIN_VALID_PRICE_USD.get(p.listing_type.value, 0)
        if p.current_price_usd is None or p.current_price_usd < min_price:
            invalid_props.append(p)
        else:
            key = (p.property_type, p.listing_type)
            groups.setdefault(key, []).append(p)

    # Clear scores for properties with invalid prices
    for p in invalid_props:
        p.price_score = None

    scored = 0
    for key, members in groups.items():
        if len(members) < 5:
            for p in members:
                p.price_score = None
            continue

        values = sorted([p.current_price_usd for p in members])
        total = len(values)

        for p in members:
            count_le = sum(1 for v in values if v <= p.current_price_usd)
            percentile = count_le / total
            # Low percentile (cheap) = high score (good price)
            score = round((1 - percentile) * 100)
            p.price_score = max(1, min(100, score))
            scored += 1

    logger.info(f"Scored {scored} properties across {len(groups)} groups ({len(invalid_props)} with invalid prices skipped)")
    return scored


def compute_overall_scores(db: Session) -> int:
    """Compute overall_score as average of available sub-scores (price, zone, condition).

    - 3 scores available: average of all 3
    - 2 scores available: average of 2
    - 1 score available: overall = that score
    - 0 scores: overall = None
    """
    props = (
        db.query(Property)
        .filter(Property.is_active == True)
        .all()
    )

    scored = 0
    for prop in props:
        scores = [s for s in (prop.price_score, prop.zone_score, prop.condition_score) if s is not None]
        if scores:
            prop.overall_score = round(sum(scores) / len(scores))
            scored += 1
        else:
            prop.overall_score = None

    db.commit()
    logger.info(f"Computed overall scores for {scored} properties")
    return scored


def get_price_context(db: Session, property_id: int) -> dict | None:
    """Get price context for a property within its group (property_type, listing_type)."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop or prop.current_price_usd is None:
        return None

    peers = (
        db.query(Property.current_price_usd)
        .filter(
            Property.is_active == True,
            Property.property_type == prop.property_type,
            Property.listing_type == prop.listing_type,
            Property.current_price_usd.isnot(None),
        )
        .all()
    )

    values = sorted([r[0] for r in peers])
    if len(values) < 5:
        return None

    mid = len(values) // 2
    median = values[mid] if len(values) % 2 == 1 else round((values[mid - 1] + values[mid]) / 2, 2)

    return {
        "price_usd": round(prop.current_price_usd, 0),
        "median_usd": round(median, 0),
        "min_usd": round(values[0], 0),
        "max_usd": round(values[-1], 0),
        "comparables_count": len(values),
        "property_type": prop.property_type.value,
        "listing_type": prop.listing_type.value,
        "price_per_m2_usd": prop.price_per_m2_usd,
        "median_per_m2_usd": None,
    }
