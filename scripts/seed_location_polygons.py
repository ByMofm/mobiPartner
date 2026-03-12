#!/usr/bin/env python3
"""Seed location polygons from OpenStreetMap for Tucumán neighborhoods.

Uses Overpass API to download admin boundaries and Nominatim for geocoding.

Usage:
    python scripts/seed_location_polygons.py
"""
import json
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Overpass query for Tucumán admin boundaries (barrios + ciudades)
OVERPASS_QUERY = """
[out:json][timeout:60];
area["name"="Tucumán"]["admin_level"="4"]->.tucuman;
(
  relation["admin_level"~"[6-9]"]["boundary"="administrative"](area.tucuman);
);
out body;
>;
out skel qt;
"""


def fetch_overpass_boundaries() -> list[dict]:
    """Fetch admin boundaries for Tucumán from Overpass API."""
    try:
        import requests
    except ImportError:
        logger.error("requests not installed")
        return []

    logger.info("Querying Overpass API for Tucumán boundaries...")
    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": OVERPASS_QUERY},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Overpass API failed: {e}")
        return []

    # Extract relations with names
    elements = data.get("elements", [])
    relations = [e for e in elements if e["type"] == "relation" and "name" in e.get("tags", {})]
    logger.info(f"Found {len(relations)} named boundaries")

    # Build node lookup for constructing polygons
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in elements if e["type"] == "node"}
    ways = {}
    for e in elements:
        if e["type"] == "way":
            coords = [nodes[n] for n in e.get("nds", []) if n in nodes]
            if coords:
                ways[e["id"]] = coords

    results = []
    for rel in relations:
        tags = rel.get("tags", {})
        name = tags.get("name", "")
        admin_level = tags.get("admin_level", "")

        # Build polygon from way members
        outer_coords = []
        for member in rel.get("members", []):
            if member["type"] == "way" and member.get("role") in ("outer", ""):
                way_coords = ways.get(member["ref"], [])
                outer_coords.extend(way_coords)

        if not outer_coords or len(outer_coords) < 4:
            continue

        # Close polygon if not closed
        if outer_coords[0] != outer_coords[-1]:
            outer_coords.append(outer_coords[0])

        # Compute centroid (simple average)
        lons = [c[0] for c in outer_coords]
        lats = [c[1] for c in outer_coords]
        centroid = (sum(lons) / len(lons), sum(lats) / len(lats))

        # Map admin_level to location level
        level = "barrio" if admin_level in ("8", "9") else "ciudad" if admin_level == "7" else "departamento"

        results.append({
            "name": name,
            "level": level,
            "admin_level": admin_level,
            "polygon_coords": outer_coords,
            "centroid": centroid,
        })

    return results


def geocode_location(name: str, state: str = "Tucumán") -> dict | None:
    """Use Nominatim to geocode a location name as fallback."""
    try:
        import requests
    except ImportError:
        return None

    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{name}, {state}, Argentina",
                "format": "json",
                "limit": 1,
                "polygon_geojson": 1,
            },
            headers={"User-Agent": "mobiPartner/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return results[0]
    except Exception as e:
        logger.debug(f"Nominatim failed for {name}: {e}")

    return None


def load_to_db(boundaries: list[dict]):
    """Load boundaries into locations table, updating geom and centroid."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from sqlalchemy import func
    from app.database import SessionLocal
    from app.models.location import Location

    db = SessionLocal()
    try:
        updated = 0
        created = 0
        for b in boundaries:
            name = b["name"]
            level = b["level"]
            coords = b["polygon_coords"]
            centroid = b["centroid"]

            # Find existing location by name (case-insensitive)
            loc = db.query(Location).filter(
                func.lower(Location.name) == name.lower(),
                Location.level == level,
            ).first()

            wkt_polygon = "POLYGON((" + ", ".join(f"{c[0]} {c[1]}" for c in coords) + "))"
            wkt_point = f"POINT({centroid[0]} {centroid[1]})"

            if loc:
                loc.geom = func.ST_GeomFromText(wkt_polygon, 4326)
                loc.centroid = func.ST_GeomFromText(wkt_point, 4326)
                updated += 1
            else:
                loc = Location(
                    name=name,
                    level=level,
                    geom=func.ST_GeomFromText(wkt_polygon, 4326),
                    centroid=func.ST_GeomFromText(wkt_point, 4326),
                )
                db.add(loc)
                created += 1

        db.commit()
        logger.info(f"Updated {updated} locations, created {created} new ones")
    finally:
        db.close()


def main():
    boundaries = fetch_overpass_boundaries()

    if boundaries:
        # Save intermediate JSON for review
        output = Path(__file__).parent / "location_polygons.json"
        # Don't save full coords to JSON (too large), just metadata
        meta = [{"name": b["name"], "level": b["level"], "coords_count": len(b["polygon_coords"])} for b in boundaries]
        output.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        logger.info(f"Saved {len(meta)} boundary metadata to {output}")

        load_to_db(boundaries)
    else:
        logger.warning("No boundaries fetched — try running again later or check network")

        # Fallback: use Nominatim for known locations
        logger.info("Attempting Nominatim fallback for known neighborhoods...")
        known = [
            "Yerba Buena", "Centro", "Barrio Norte", "Barrio Sur",
            "Tafi Viejo", "Las Talitas", "Lules", "Concepcion",
        ]
        for name in known:
            result = geocode_location(name)
            if result:
                logger.info(f"  Found: {name} at {result.get('lat')}, {result.get('lon')}")
            time.sleep(1.1)  # Nominatim rate limit


if __name__ == "__main__":
    main()
