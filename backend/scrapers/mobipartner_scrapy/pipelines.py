import logging
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import func

from app.models.property import Property, PropertyListing, PriceHistory, ScrapeRun
from app.models.enums import PropertyType, ListingType, CurrencyType, SourceType
from app.database import Base
from app.services.dedup import normalize_address, find_duplicate
from app.utils.currency import get_usd_ars_blue_rate_sync, convert_to_usd
from app.config import settings

logger = logging.getLogger(__name__)


class PropertyPipeline:
    def __init__(self, database_url):
        self.database_url = database_url
        self.session = None
        self.scrape_run = None
        self.usd_ars_rate = None
        self.counts = {"found": 0, "new": 0, "updated": 0, "errors": 0}

    @classmethod
    def from_crawler(cls, crawler):
        return cls(database_url=crawler.settings.get("DATABASE_URL"))

    def open_spider(self, spider):
        connect_args = {}
        if "supabase" in self.database_url or "sslmode" in self.database_url:
            connect_args["sslmode"] = "require"
        engine = create_engine(self.database_url, connect_args=connect_args)
        Session = sessionmaker(bind=engine)
        self.session = Session()

        self.usd_ars_rate = get_usd_ars_blue_rate_sync(fallback=settings.usd_ars_rate_fallback)
        logger.info(f"USD/ARS blue rate: {self.usd_ars_rate}")

        source = SourceType(spider.name)
        self.scrape_run = ScrapeRun(source=source, started_at=datetime.utcnow())
        self.session.add(self.scrape_run)
        self.session.commit()
        logger.info(f"Started scrape run {self.scrape_run.id} for {spider.name}")

    def close_spider(self, spider):
        if self.scrape_run:
            self.scrape_run.finished_at = datetime.utcnow()
            self.scrape_run.items_found = self.counts["found"]
            self.scrape_run.items_new = self.counts["new"]
            self.scrape_run.items_updated = self.counts["updated"]
            self.scrape_run.items_errors = self.counts["errors"]
            self.session.commit()
            logger.info(f"Scrape run {self.scrape_run.id} finished: {self.counts}")

        if self.session:
            self.session.close()

    def process_item(self, item, spider):
        self.counts["found"] += 1
        try:
            self._upsert_listing(item)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            self.counts["errors"] += 1
            logger.error(f"Error processing item {item.get('source_id')}: {e}")
        return item

    def _upsert_listing(self, item):
        source = SourceType(item["source"])
        source_id = item["source_id"]

        existing = (
            self.session.query(PropertyListing)
            .filter(PropertyListing.source == source, PropertyListing.source_id == source_id)
            .first()
        )

        price = item.get("price")
        currency_str = item.get("currency")
        currency = CurrencyType(currency_str) if currency_str else None

        if existing:
            # Check for price change
            price_changed = existing.original_price != price or existing.original_currency != currency

            existing.original_title = item.get("title")
            existing.original_address = item.get("address")
            existing.original_price = price
            existing.original_currency = currency
            existing.image_urls = item.get("image_urls", [])
            existing.raw_data = item.get("raw_data", {})
            existing.is_active = True
            existing.updated_at = datetime.utcnow()

            if price_changed and price is not None and currency is not None:
                self._record_price(existing, price, currency)
                self.counts["updated"] += 1

                # Update property current price
                if existing.property_id:
                    prop = self.session.query(Property).get(existing.property_id)
                    if prop:
                        prop.current_price = price
                        prop.current_currency = currency
                        prop.current_price_usd = convert_to_usd(price, currency.value, self.usd_ars_rate)
                        if prop.current_price_usd and prop.total_area_m2 and prop.total_area_m2 > 0:
                            prop.price_per_m2_usd = round(prop.current_price_usd / prop.total_area_m2, 2)
                        prop.last_seen_at = datetime.utcnow()
            else:
                if existing.property_id:
                    prop = self.session.query(Property).get(existing.property_id)
                    if prop:
                        prop.last_seen_at = datetime.utcnow()
        else:
            # Create new listing, try dedup first
            property_type = self._parse_property_type(item.get("property_type", ""))
            listing_type = self._parse_listing_type(item.get("listing_type", ""))
            address = item.get("address")
            address_norm = normalize_address(address)

            # Create the listing first (without property_id)
            listing = PropertyListing(
                source=source,
                source_url=item.get("source_url", ""),
                source_id=source_id,
                original_title=item.get("title"),
                original_address=address,
                original_price=price,
                original_currency=currency,
                image_urls=item.get("image_urls", []),
                raw_data=item.get("raw_data", {}),
            )
            self.session.add(listing)
            self.session.flush()

            # Try to find a duplicate property
            match = find_duplicate(
                db=self.session,
                listing=listing,
                property_type=property_type,
                listing_type=listing_type,
                address_normalized=address_norm,
                total_area=item.get("total_area_m2"),
                rooms=item.get("rooms"),
                price=price,
                lat=None,
                lng=None,
            )

            lat = item.get("latitude")
            lng = item.get("longitude")

            if match:
                # Link to existing property
                listing.property_id = match.id
                match.last_seen_at = datetime.utcnow()
                # Update coordinates if not yet set
                if lat and lng and not match.latitude:
                    match.latitude = lat
                    match.longitude = lng
                    match.geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
                # Update apto_credito if newly detected
                if item.get("apto_credito") and not match.apto_credito:
                    match.apto_credito = True
                prop = match
            else:
                # Create new property
                price_usd = convert_to_usd(price, currency.value, self.usd_ars_rate) if price and currency else None
                area = item.get("total_area_m2")
                price_per_m2 = round(price_usd / area, 2) if price_usd and area and area > 0 else None
                prop = Property(
                    property_type=property_type,
                    listing_type=listing_type,
                    address=address,
                    address_normalized=address_norm,
                    current_price=price,
                    current_currency=currency,
                    current_price_usd=price_usd,
                    price_per_m2_usd=price_per_m2,
                    total_area_m2=area,
                    covered_area_m2=item.get("covered_area_m2"),
                    rooms=item.get("rooms"),
                    bedrooms=item.get("bedrooms"),
                    bathrooms=item.get("bathrooms"),
                    garages=item.get("garages"),
                    age_years=item.get("age_years"),
                    floor_number=item.get("floor_number"),
                    expenses_ars=item.get("expenses_ars"),
                    apto_credito=bool(item.get("apto_credito")),
                    latitude=lat,
                    longitude=lng,
                    first_seen_at=datetime.utcnow(),
                    last_seen_at=datetime.utcnow(),
                )
                if lat and lng:
                    prop.geom = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
                self.session.add(prop)
                self.session.flush()
                listing.property_id = prop.id

            if price is not None and currency is not None:
                self._record_price(listing, price, currency)

            self.counts["new"] += 1

    def _record_price(self, listing, price, currency):
        price_usd = convert_to_usd(price, currency.value, self.usd_ars_rate)
        history = PriceHistory(
            property_listing_id=listing.id,
            property_id=listing.property_id,
            price=price,
            currency=currency,
            price_usd=price_usd,
            usd_ars_rate=self.usd_ars_rate,
            scraped_at=datetime.utcnow(),
        )
        self.session.add(history)

    def _parse_property_type(self, value: str) -> PropertyType:
        mapping = {
            "departamento": PropertyType.APARTMENT,
            "departamentos": PropertyType.APARTMENT,
            "casa": PropertyType.HOUSE,
            "casas": PropertyType.HOUSE,
            "ph": PropertyType.PH,
            "terreno": PropertyType.LAND,
            "terrenos": PropertyType.LAND,
            "local": PropertyType.COMMERCIAL,
            "locales": PropertyType.COMMERCIAL,
            "oficina": PropertyType.OFFICE,
            "oficinas": PropertyType.OFFICE,
            "cochera": PropertyType.GARAGE,
            "cocheras": PropertyType.GARAGE,
            "galpon": PropertyType.WAREHOUSE,
            "galpones": PropertyType.WAREHOUSE,
            "deposito": PropertyType.WAREHOUSE,
        }
        return mapping.get(value.lower().strip(), PropertyType.APARTMENT)

    def _parse_listing_type(self, value: str) -> ListingType:
        mapping = {
            "venta": ListingType.SALE,
            "alquiler": ListingType.RENT,
            "alquiler-temporario": ListingType.TEMPORARY_RENT,
            "alquiler temporario": ListingType.TEMPORARY_RENT,
        }
        return mapping.get(value.lower().strip(), ListingType.SALE)
