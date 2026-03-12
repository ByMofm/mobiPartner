"""Seed sample property data for development/demo purposes."""

import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.property import Property, PropertyListing, PriceHistory
from app.models.enums import PropertyType, ListingType, CurrencyType, SourceType
from app.config import settings

# Tucumán neighborhoods with approximate coordinates
LOCATIONS = [
    {"name": "Centro", "lat": -26.8241, "lng": -65.2226},
    {"name": "Barrio Norte", "lat": -26.8150, "lng": -65.2180},
    {"name": "Barrio Sur", "lat": -26.8350, "lng": -65.2200},
    {"name": "Yerba Buena", "lat": -26.8160, "lng": -65.2570},
    {"name": "Parque 9 de Julio", "lat": -26.8280, "lng": -65.2100},
    {"name": "Villa Luján", "lat": -26.8400, "lng": -65.2350},
    {"name": "Marcos Paz", "lat": -26.8100, "lng": -65.2400},
    {"name": "Barrio Jardín", "lat": -26.8050, "lng": -65.2300},
    {"name": "Ciudadela", "lat": -26.8190, "lng": -65.2050},
    {"name": "Las Talitas", "lat": -26.7900, "lng": -65.2100},
    {"name": "Tafí Viejo", "lat": -26.7320, "lng": -65.2570},
    {"name": "Banda del Río Salí", "lat": -26.8500, "lng": -65.1650},
]

STREETS = [
    "Av. Mate de Luna", "Av. Aconquija", "Av. Sarmiento", "Av. Mitre",
    "San Martín", "24 de Septiembre", "Maipú", "Las Piedras",
    "Junín", "Laprida", "Muñecas", "Corrientes",
    "Santiago del Estero", "Catamarca", "Mendoza", "San Juan",
    "Crisóstomo Álvarez", "Av. Roca", "Av. Belgrano", "Av. Independencia",
    "Monteagudo", "Av. Colón", "Pueyrredón", "Rivadavia",
]

TITLES_SALE = [
    "Departamento luminoso en {barrio}",
    "Casa amplia con jardín en {barrio}",
    "Excelente PH reciclado en {barrio}",
    "Terreno ideal para construir en {barrio}",
    "Departamento 2 ambientes a estrenar en {barrio}",
    "Casa 3 dormitorios con pileta en {barrio}",
    "Monoambiente con balcón en {barrio}",
    "Dúplex moderno en {barrio}",
    "Departamento con cochera en {barrio}",
    "Casa en barrio cerrado en {barrio}",
]

TITLES_RENT = [
    "Alquiler departamento en {barrio}",
    "Casa en alquiler en {barrio}",
    "Alquiler temporario en {barrio}",
    "Monoambiente amoblado en {barrio}",
    "Departamento 1 dormitorio en {barrio}",
]


def random_jitter(base, jitter=0.005):
    return base + random.uniform(-jitter, jitter)


def generate_properties():
    props = []

    # Apartments for sale
    for i in range(60):
        loc = random.choice(LOCATIONS)
        bedrooms = random.choice([1, 1, 2, 2, 2, 3, 3])
        total_area = random.randint(30, 120) + bedrooms * 10
        covered_area = int(total_area * random.uniform(0.85, 1.0))
        price_usd = random.randint(35000, 150000)
        street = random.choice(STREETS)
        number = random.randint(100, 3500)

        props.append({
            "property_type": PropertyType.APARTMENT,
            "listing_type": ListingType.SALE,
            "address": f"{street} {number}, {loc['name']}, Tucumán",
            "lat": random_jitter(loc["lat"]),
            "lng": random_jitter(loc["lng"]),
            "price": price_usd,
            "currency": CurrencyType.USD,
            "total_area": total_area,
            "covered_area": covered_area,
            "rooms": bedrooms + 1,
            "bedrooms": bedrooms,
            "bathrooms": max(1, bedrooms - 1),
            "garages": random.choice([0, 0, 0, 1, 1]),
            "expenses": random.choice([None, None, 15000, 25000, 35000, 50000]),
            "title": random.choice(TITLES_SALE).format(barrio=loc["name"]),
            "source": random.choice([SourceType.ZONAPROP, SourceType.ARGENPROP, SourceType.MERCADOLIBRE]),
            "barrio": loc["name"],
        })

    # Houses for sale
    for i in range(30):
        loc = random.choice(LOCATIONS)
        bedrooms = random.choice([2, 3, 3, 4, 4, 5])
        total_area = random.randint(150, 500)
        covered_area = int(total_area * random.uniform(0.5, 0.8))
        price_usd = random.randint(60000, 350000)
        street = random.choice(STREETS)
        number = random.randint(100, 3500)

        props.append({
            "property_type": PropertyType.HOUSE,
            "listing_type": ListingType.SALE,
            "address": f"{street} {number}, {loc['name']}, Tucumán",
            "lat": random_jitter(loc["lat"]),
            "lng": random_jitter(loc["lng"]),
            "price": price_usd,
            "currency": CurrencyType.USD,
            "total_area": total_area,
            "covered_area": covered_area,
            "rooms": bedrooms + 2,
            "bedrooms": bedrooms,
            "bathrooms": max(1, bedrooms - 1),
            "garages": random.choice([0, 1, 1, 2]),
            "expenses": None,
            "title": random.choice(TITLES_SALE).format(barrio=loc["name"]),
            "source": random.choice([SourceType.ZONAPROP, SourceType.ARGENPROP]),
            "barrio": loc["name"],
        })

    # Apartments for rent
    for i in range(40):
        loc = random.choice(LOCATIONS)
        bedrooms = random.choice([1, 1, 2, 2, 3])
        total_area = random.randint(30, 100) + bedrooms * 10
        covered_area = int(total_area * random.uniform(0.85, 1.0))
        price_ars = random.randint(150000, 600000)
        street = random.choice(STREETS)
        number = random.randint(100, 3500)

        props.append({
            "property_type": PropertyType.APARTMENT,
            "listing_type": ListingType.RENT,
            "address": f"{street} {number}, {loc['name']}, Tucumán",
            "lat": random_jitter(loc["lat"]),
            "lng": random_jitter(loc["lng"]),
            "price": price_ars,
            "currency": CurrencyType.ARS,
            "total_area": total_area,
            "covered_area": covered_area,
            "rooms": bedrooms + 1,
            "bedrooms": bedrooms,
            "bathrooms": 1,
            "garages": 0,
            "expenses": random.choice([None, 10000, 20000, 30000]),
            "title": random.choice(TITLES_RENT).format(barrio=loc["name"]),
            "source": random.choice([SourceType.ZONAPROP, SourceType.ARGENPROP, SourceType.MERCADOLIBRE]),
            "barrio": loc["name"],
        })

    # Land for sale
    for i in range(15):
        loc = random.choice(LOCATIONS)
        total_area = random.randint(200, 2000)
        price_usd = random.randint(15000, 120000)
        street = random.choice(STREETS)
        number = random.randint(100, 3500)

        props.append({
            "property_type": PropertyType.LAND,
            "listing_type": ListingType.SALE,
            "address": f"{street} {number}, {loc['name']}, Tucumán",
            "lat": random_jitter(loc["lat"]),
            "lng": random_jitter(loc["lng"]),
            "price": price_usd,
            "currency": CurrencyType.USD,
            "total_area": total_area,
            "covered_area": None,
            "rooms": None,
            "bedrooms": None,
            "bathrooms": None,
            "garages": None,
            "expenses": None,
            "title": f"Terreno {total_area}m² en {loc['name']}",
            "source": random.choice([SourceType.ZONAPROP, SourceType.ARGENPROP]),
            "barrio": loc["name"],
        })

    # PH for sale
    for i in range(10):
        loc = random.choice(LOCATIONS)
        bedrooms = random.choice([2, 3, 3])
        total_area = random.randint(80, 180)
        covered_area = int(total_area * random.uniform(0.7, 0.9))
        price_usd = random.randint(45000, 130000)
        street = random.choice(STREETS)
        number = random.randint(100, 3500)

        props.append({
            "property_type": PropertyType.PH,
            "listing_type": ListingType.SALE,
            "address": f"{street} {number}, {loc['name']}, Tucumán",
            "lat": random_jitter(loc["lat"]),
            "lng": random_jitter(loc["lng"]),
            "price": price_usd,
            "currency": CurrencyType.USD,
            "total_area": total_area,
            "covered_area": covered_area,
            "rooms": bedrooms + 1,
            "bedrooms": bedrooms,
            "bathrooms": max(1, bedrooms - 1),
            "garages": random.choice([0, 1]),
            "expenses": random.choice([None, 8000, 15000]),
            "title": f"PH {bedrooms} dormitorios en {loc['name']}",
            "source": random.choice([SourceType.ZONAPROP, SourceType.ARGENPROP]),
            "barrio": loc["name"],
        })

    return props


def main():
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Check if data already exists
    count = session.query(Property).count()
    if count > 0:
        print(f"Database already has {count} properties. Skipping seed.")
        session.close()
        return

    props_data = generate_properties()
    print(f"Seeding {len(props_data)} sample properties...")

    now = datetime.utcnow()

    for i, p in enumerate(props_data):
        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

        days_ago = random.randint(0, 90)
        first_seen = now - timedelta(days=days_ago)

        prop = Property(
            property_type=p["property_type"],
            listing_type=p["listing_type"],
            address=p["address"],
            latitude=p["lat"],
            longitude=p["lng"],
            geom=ST_SetSRID(ST_MakePoint(p["lng"], p["lat"]), 4326),
            current_price=p["price"],
            current_currency=p["currency"],
            current_price_usd=p["price"] if p["currency"] == CurrencyType.USD else round(p["price"] / 1200, 2),
            total_area_m2=p["total_area"],
            covered_area_m2=p["covered_area"],
            rooms=p["rooms"],
            bedrooms=p["bedrooms"],
            bathrooms=p["bathrooms"],
            garages=p["garages"],
            expenses_ars=p["expenses"],
            price_per_m2_usd=(
                round(p["price"] / p["total_area"], 2) if p["currency"] == CurrencyType.USD and p["total_area"]
                else None
            ),
            first_seen_at=first_seen,
            last_seen_at=now - timedelta(days=random.randint(0, 3)),
            is_active=True,
        )
        session.add(prop)
        session.flush()

        source_id = f"sample-{p['source'].value}-{i:04d}"
        listing = PropertyListing(
            property_id=prop.id,
            source=p["source"],
            source_url=f"https://www.{p['source'].value}.com.ar/propiedad/{source_id}",
            source_id=source_id,
            original_title=p["title"],
            original_address=p["address"],
            original_price=p["price"],
            original_currency=p["currency"],
            image_urls=[],
            raw_data={"sample": True, "barrio": p["barrio"]},
        )
        session.add(listing)
        session.flush()

        # Price history: initial + maybe a change
        history = PriceHistory(
            property_listing_id=listing.id,
            property_id=prop.id,
            price=p["price"],
            currency=p["currency"],
            price_usd=p["price"] if p["currency"] == CurrencyType.USD else round(p["price"] / 1200, 2),
            scraped_at=first_seen,
        )
        session.add(history)

        # 30% chance of a price change
        if random.random() < 0.3:
            change = random.uniform(0.9, 1.1)
            new_price = round(p["price"] * change)
            history2 = PriceHistory(
                property_listing_id=listing.id,
                property_id=prop.id,
                price=new_price,
                currency=p["currency"],
                price_usd=new_price if p["currency"] == CurrencyType.USD else round(new_price / 1200, 2),
                scraped_at=now - timedelta(days=random.randint(0, 30)),
            )
            session.add(history2)

        # 15% chance of a second listing (different source)
        if random.random() < 0.15:
            other_sources = [s for s in SourceType if s != p["source"]]
            other_source = random.choice(other_sources)
            source_id2 = f"sample-{other_source.value}-{i:04d}-dup"
            listing2 = PropertyListing(
                property_id=prop.id,
                source=other_source,
                source_url=f"https://www.{other_source.value}.com.ar/propiedad/{source_id2}",
                source_id=source_id2,
                original_title=p["title"],
                original_address=p["address"],
                original_price=p["price"],
                original_currency=p["currency"],
                image_urls=[],
                raw_data={"sample": True, "duplicate": True},
            )
            session.add(listing2)

    session.commit()
    session.close()
    print(f"Done! Seeded {len(props_data)} properties with listings and price history.")


if __name__ == "__main__":
    main()
