"""Initialize database schema and extensions."""

from sqlalchemy import text

from app.database import engine, Base
from app.models import *  # noqa: F401, F403


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    # Create additional indexes that SQLAlchemy doesn't handle
    with engine.connect() as conn:
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_properties_address_trgm
                ON properties USING gin (address_normalized gin_trgm_ops)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_properties_type_listing
                ON properties (property_type, listing_type)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_properties_location
                ON properties (location_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_price_history_listing
                ON price_history (property_listing_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_price_history_property
                ON price_history (property_id)
            """)
        )
        conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS idx_price_history_scraped
                ON price_history (scraped_at)
            """)
        )
        conn.commit()

    print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
