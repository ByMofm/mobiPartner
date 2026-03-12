"""Scrape MercadoLibre real estate via their public API (no Scrapy)."""

import sys
import os
import re
import time
import logging

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.property import Property, PropertyListing, PriceHistory, ScrapeRun
from app.models.enums import PropertyType, ListingType, CurrencyType, SourceType
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE = "https://api.mercadolibre.com"
CATEGORY = "MLA1459"
STATE_ID = "TUxBUFRVQ2E1YmU3"

SUBCATEGORIES = {
    "MLA1472": PropertyType.APARTMENT,
    "MLA1493": PropertyType.HOUSE,
    "MLA1473": PropertyType.LAND,
    "MLA1477": PropertyType.PH,
    "MLA1492": PropertyType.COMMERCIAL,
    "MLA50547": PropertyType.OFFICE,
    "MLA1474": PropertyType.GARAGE,
    "MLA1476": PropertyType.WAREHOUSE,
}

OPERATION_MAP = {
    "242073": ListingType.SALE,
    "242074": ListingType.RENT,
    "242075": ListingType.TEMPORARY_RENT,
}


def get_attr(attributes, attr_id):
    for a in attributes:
        if a.get("id") == attr_id:
            return a.get("value_number") or a.get("value_name")
    return None


def get_attr_number(attributes, *attr_ids):
    for attr_id in attr_ids:
        val = get_attr(attributes, attr_id)
        if val is not None:
            if isinstance(val, (int, float)):
                return float(val)
            match = re.search(r"[\d.,]+", str(val))
            if match:
                try:
                    return float(match.group().replace(",", "."))
                except ValueError:
                    pass
    return None


def main():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    scrape_run = ScrapeRun(source=SourceType.MERCADOLIBRE, started_at=datetime.utcnow())
    session.add(scrape_run)
    session.commit()

    counts = {"found": 0, "new": 0, "updated": 0, "errors": 0}
    client = httpx.Client(
        timeout=15,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        },
    )

    offset = 0
    limit = 50
    max_results = 1000

    while offset < max_results:
        url = f"{API_BASE}/sites/MLA/search?category={CATEGORY}&state={STATE_ID}&limit={limit}&offset={offset}"
        logger.info(f"Fetching: offset={offset}")

        try:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error(f"API error at offset {offset}: {e}")
            break

        results = data.get("results", [])
        total = data.get("paging", {}).get("total", 0)
        logger.info(f"Got {len(results)} results, total={total}")

        if not results:
            break

        for result in results:
            counts["found"] += 1
            try:
                process_result(session, result, client, counts)
                session.commit()
            except Exception as e:
                session.rollback()
                counts["errors"] += 1
                logger.error(f"Error processing {result.get('id')}: {e}")

        offset += limit
        if offset >= min(total, max_results):
            break

        time.sleep(1)

    client.close()

    scrape_run.finished_at = datetime.utcnow()
    scrape_run.items_found = counts["found"]
    scrape_run.items_new = counts["new"]
    scrape_run.items_updated = counts["updated"]
    scrape_run.items_errors = counts["errors"]
    session.commit()
    session.close()

    logger.info(f"Done! {counts}")


def process_result(session, result, client, counts):
    item_id = result.get("id", "")
    if not item_id:
        return

    source = SourceType.MERCADOLIBRE

    # Check existing
    existing = (
        session.query(PropertyListing)
        .filter(PropertyListing.source == source, PropertyListing.source_id == item_id)
        .first()
    )

    # Parse data
    price = result.get("price")
    currency_id = result.get("currency_id", "")
    currency = CurrencyType.USD if currency_id == "USD" else CurrencyType.ARS

    title = result.get("title", "")
    permalink = result.get("permalink", "")

    location = result.get("location", {})
    city = location.get("city", {}).get("name", "")
    neighborhood = location.get("neighborhood", {}).get("name", "")
    address_parts = [p for p in [neighborhood, city, "Tucumán"] if p]
    address = ", ".join(address_parts)

    attributes = result.get("attributes", [])

    category_id = result.get("category_id", "")
    property_type = SUBCATEGORIES.get(category_id, PropertyType.APARTMENT)

    listing_type = ListingType.SALE
    for attr in attributes:
        if attr.get("id") == "OPERATION":
            listing_type = OPERATION_MAP.get(attr.get("value_id", ""), ListingType.SALE)
            break

    total_area = get_attr_number(attributes, "TOTAL_AREA")
    covered_area = get_attr_number(attributes, "COVERED_AREA")
    rooms = get_attr_number(attributes, "ROOMS")
    bedrooms = get_attr_number(attributes, "BEDROOMS")
    bathrooms = get_attr_number(attributes, "FULL_BATHROOMS", "BATHROOMS")
    garages = get_attr_number(attributes, "PARKING_LOTS")

    # Images
    pictures = result.get("pictures", [])
    if pictures:
        image_urls = [p.get("url") or p.get("secure_url", "") for p in pictures]
    else:
        thumb = result.get("thumbnail", "")
        image_urls = [thumb] if thumb else []

    # Fetch detail for more data
    detail_data = {}
    try:
        detail_resp = client.get(f"{API_BASE}/items/{item_id}")
        if detail_resp.status_code == 200:
            detail_data = detail_resp.json()
            detail_attrs = detail_data.get("attributes", [])
            if detail_attrs:
                if not total_area:
                    total_area = get_attr_number(detail_attrs, "TOTAL_AREA")
                if not covered_area:
                    covered_area = get_attr_number(detail_attrs, "COVERED_AREA")
                if not rooms:
                    rooms = get_attr_number(detail_attrs, "ROOMS")
                if not bedrooms:
                    bedrooms = get_attr_number(detail_attrs, "BEDROOMS")
                if not bathrooms:
                    bathrooms = get_attr_number(detail_attrs, "FULL_BATHROOMS", "BATHROOMS")
            detail_pics = detail_data.get("pictures", [])
            if detail_pics:
                image_urls = [p.get("url") or p.get("secure_url", "") for p in detail_pics]
        time.sleep(0.5)
    except Exception:
        pass

    if existing:
        price_changed = existing.original_price != price or existing.original_currency != currency
        existing.original_title = title
        existing.original_address = address
        existing.original_price = price
        existing.original_currency = currency
        existing.image_urls = image_urls
        existing.raw_data = detail_data or result
        existing.is_active = True
        existing.updated_at = datetime.utcnow()

        if price_changed and price is not None:
            history = PriceHistory(
                property_listing_id=existing.id,
                property_id=existing.property_id,
                price=price,
                currency=currency,
                scraped_at=datetime.utcnow(),
            )
            session.add(history)
            counts["updated"] += 1

            if existing.property_id:
                prop = session.query(Property).get(existing.property_id)
                if prop:
                    prop.current_price = price
                    prop.current_currency = currency
                    prop.last_seen_at = datetime.utcnow()
        else:
            if existing.property_id:
                prop = session.query(Property).get(existing.property_id)
                if prop:
                    prop.last_seen_at = datetime.utcnow()
    else:
        prop = Property(
            property_type=property_type,
            listing_type=listing_type,
            address=address,
            current_price=price,
            current_currency=currency,
            total_area_m2=total_area,
            covered_area_m2=covered_area,
            rooms=int(rooms) if rooms else None,
            bedrooms=int(bedrooms) if bedrooms else None,
            bathrooms=int(bathrooms) if bathrooms else None,
            garages=int(garages) if garages else None,
            first_seen_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        session.add(prop)
        session.flush()

        listing = PropertyListing(
            property_id=prop.id,
            source=source,
            source_url=permalink,
            source_id=item_id,
            original_title=title,
            original_address=address,
            original_price=price,
            original_currency=currency,
            image_urls=image_urls,
            raw_data=detail_data or result,
        )
        session.add(listing)
        session.flush()

        if price is not None:
            history = PriceHistory(
                property_listing_id=listing.id,
                property_id=prop.id,
                price=price,
                currency=currency,
                scraped_at=datetime.utcnow(),
            )
            session.add(history)

        counts["new"] += 1


if __name__ == "__main__":
    main()
