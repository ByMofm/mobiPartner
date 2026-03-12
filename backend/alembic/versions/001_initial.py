"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Enum types (created via raw SQL to avoid conflicts with SQLAlchemy auto-creation)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE propertytype AS ENUM ('apartment','house','ph','land','commercial','office','garage','warehouse');
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE listingtype AS ENUM ('sale','rent','temporary_rent');
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE currencytype AS ENUM ('ARS','USD');
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE sourcetype AS ENUM ('zonaprop','argenprop','mercadolibre');
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)

    # Use create_type=False since we already created them above
    property_type = sa.Enum('apartment','house','ph','land','commercial','office','garage','warehouse', name='propertytype', create_type=False)
    listing_type = sa.Enum('sale','rent','temporary_rent', name='listingtype', create_type=False)
    currency_type = sa.Enum('ARS','USD', name='currencytype', create_type=False)
    source_type = sa.Enum('zonaprop','argenprop','mercadolibre', name='sourcetype', create_type=False)

    # locations
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("level", sa.String(50), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POLYGON", srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
    )

    # properties
    op.create_table(
        "properties",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("property_type", property_type, nullable=False),
        sa.Column("listing_type", listing_type, nullable=False),
        sa.Column("location_id", sa.Integer, sa.ForeignKey("locations.id"), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("address_normalized", sa.String(500), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("geom", geoalchemy2.Geometry("POINT", srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=True),
        sa.Column("current_price", sa.Float, nullable=True),
        sa.Column("current_currency", currency_type, nullable=True),
        sa.Column("current_price_usd", sa.Float, nullable=True),
        sa.Column("total_area_m2", sa.Float, nullable=True),
        sa.Column("covered_area_m2", sa.Float, nullable=True),
        sa.Column("rooms", sa.Integer, nullable=True),
        sa.Column("bedrooms", sa.Integer, nullable=True),
        sa.Column("bathrooms", sa.Integer, nullable=True),
        sa.Column("garages", sa.Integer, nullable=True),
        sa.Column("age_years", sa.Integer, nullable=True),
        sa.Column("floor_number", sa.Integer, nullable=True),
        sa.Column("has_pool", sa.Boolean, default=False),
        sa.Column("has_gym", sa.Boolean, default=False),
        sa.Column("has_laundry", sa.Boolean, default=False),
        sa.Column("has_security", sa.Boolean, default=False),
        sa.Column("has_balcony", sa.Boolean, default=False),
        sa.Column("expenses_ars", sa.Float, nullable=True),
        sa.Column("price_score", sa.Integer, nullable=True),
        sa.Column("price_per_m2_usd", sa.Float, nullable=True),
        sa.Column("first_seen_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, default=True),
    )
    op.create_index("idx_properties_type_listing", "properties", ["property_type", "listing_type"])
    op.create_index("idx_properties_location", "properties", ["location_id"])
    op.create_index(
        "idx_properties_address_trgm",
        "properties",
        ["address_normalized"],
        postgresql_using="gin",
        postgresql_ops={"address_normalized": "gin_trgm_ops"},
    )

    # property_listings
    op.create_table(
        "property_listings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("property_id", sa.Integer, sa.ForeignKey("properties.id"), nullable=True),
        sa.Column("source", source_type, nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("source_id", sa.String(255), nullable=False),
        sa.Column("original_title", sa.String(500), nullable=True),
        sa.Column("original_address", sa.String(500), nullable=True),
        sa.Column("original_price", sa.Float, nullable=True),
        sa.Column("original_currency", currency_type, nullable=True),
        sa.Column("image_urls", sa.ARRAY(sa.Text), default=[]),
        sa.Column("raw_data", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_id", name="uq_source_source_id"),
    )

    # price_history
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("property_listing_id", sa.Integer, sa.ForeignKey("property_listings.id"), nullable=False),
        sa.Column("property_id", sa.Integer, sa.ForeignKey("properties.id"), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("currency", currency_type, nullable=False),
        sa.Column("price_usd", sa.Float, nullable=True),
        sa.Column("usd_ars_rate", sa.Float, nullable=True),
        sa.Column("scraped_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_price_history_listing", "price_history", ["property_listing_id"])
    op.create_index("idx_price_history_property", "price_history", ["property_id"])
    op.create_index("idx_price_history_scraped", "price_history", ["scraped_at"])

    # scrape_runs
    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", source_type, nullable=False),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("items_found", sa.Integer, default=0),
        sa.Column("items_new", sa.Integer, default=0),
        sa.Column("items_updated", sa.Integer, default=0),
        sa.Column("items_errors", sa.Integer, default=0),
        sa.Column("error_log", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("price_history")
    op.drop_table("property_listings")
    op.drop_table("properties")
    op.drop_table("locations")
    op.execute("DROP TYPE IF EXISTS sourcetype")
    op.execute("DROP TYPE IF EXISTS currencytype")
    op.execute("DROP TYPE IF EXISTS listingtype")
    op.execute("DROP TYPE IF EXISTS propertytype")
