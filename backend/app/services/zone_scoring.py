import logging
import unicodedata

from sqlalchemy.orm import Session

from app.models.property import Property
from app.models.location import Location
from app.models.zone_quality import ZoneQuality

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lowercase + remove accents."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def compute_zone_scores(db: Session) -> int:
    """Assign zone_score to properties based on their location's ZoneQuality.

    For properties with a location_id, look up the ZoneQuality for that location.
    If no ZoneQuality exists for the exact location, walk up the hierarchy
    (barrio -> ciudad -> departamento) to find the nearest one.

    For properties without location_id but with an address, try to match
    against zone quality location names as a fallback.

    Returns the number of properties scored.
    """
    # Build lookup: location_id -> overall_zone_score
    zone_qualities = db.query(ZoneQuality).all()
    zone_map: dict[int, int] = {}
    for zq in zone_qualities:
        if zq.overall_zone_score is not None:
            zone_map[zq.location_id] = zq.overall_zone_score

    if not zone_map:
        logger.warning("No zone qualities found — run scrape_crime_data.py --load first")
        return 0

    # Build parent lookup for hierarchy traversal
    locations = db.query(Location).all()
    parent_map: dict[int, int | None] = {loc.id: loc.parent_id for loc in locations}

    # Build name lookup for address-based fallback
    # (normalized_name -> list of (location_id, level_priority))
    LEVEL_PRIORITY = {"barrio": 0, "ciudad": 1, "departamento": 2, "provincia": 3}
    name_to_zone: dict[str, list[tuple[int, int]]] = {}
    for loc in locations:
        if loc.id in zone_map:
            norm = _normalize(loc.name)
            name_to_zone.setdefault(norm, []).append(
                (zone_map[loc.id], LEVEL_PRIORITY.get(loc.level, 9))
            )
    # Sort each entry so most specific (barrio) comes first
    for name in name_to_zone:
        name_to_zone[name].sort(key=lambda x: x[1])

    def find_zone_score_by_location(location_id: int | None) -> int | None:
        """Walk up the location hierarchy to find the nearest zone score."""
        visited = set()
        current = location_id
        while current is not None and current not in visited:
            visited.add(current)
            if current in zone_map:
                return zone_map[current]
            current = parent_map.get(current)
        return None

    def find_zone_score_by_address(address: str) -> int | None:
        """Try to match address text against known zone names."""
        addr_norm = _normalize(address)
        best_score = None
        best_priority = 99
        for name, entries in name_to_zone.items():
            if name in addr_norm and entries[0][1] < best_priority:
                best_score = entries[0][0]
                best_priority = entries[0][1]
        return best_score

    # Score all active properties
    props = (
        db.query(Property)
        .filter(Property.is_active == True)
        .all()
    )

    scored = 0
    for prop in props:
        score = None

        # Strategy 1: location hierarchy
        if prop.location_id is not None:
            score = find_zone_score_by_location(prop.location_id)

        # Strategy 2: address text matching
        if score is None and prop.address:
            score = find_zone_score_by_address(prop.address)

        if score is not None:
            prop.zone_score = score
            scored += 1

    db.commit()
    logger.info(f"Zone-scored {scored} out of {len(props)} active properties")
    return scored
