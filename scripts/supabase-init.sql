-- =============================================================================
-- mobiPartner: Schema completo para Supabase
-- Pegar en SQL Editor de Supabase y ejecutar
-- =============================================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enum types
DO $$ BEGIN
    CREATE TYPE propertytype AS ENUM ('apartment','house','ph','land','commercial','office','garage','warehouse');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE listingtype AS ENUM ('sale','rent','temporary_rent');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE currencytype AS ENUM ('ARS','USD');
EXCEPTION WHEN duplicate_object THEN null; END $$;

DO $$ BEGIN
    CREATE TYPE sourcetype AS ENUM ('zonaprop','argenprop','mercadolibre');
EXCEPTION WHEN duplicate_object THEN null; END $$;

-- locations
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    level VARCHAR(50) NOT NULL,
    parent_id INTEGER REFERENCES locations(id),
    geom geometry(POLYGON, 4326),
    centroid geometry(POINT, 4326)
);

-- properties
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    property_type propertytype NOT NULL,
    listing_type listingtype NOT NULL,
    location_id INTEGER REFERENCES locations(id),
    address VARCHAR(500),
    address_normalized VARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    geom geometry(POINT, 4326),
    current_price FLOAT,
    current_currency currencytype,
    current_price_usd FLOAT,
    total_area_m2 FLOAT,
    covered_area_m2 FLOAT,
    rooms INTEGER,
    bedrooms INTEGER,
    bathrooms INTEGER,
    garages INTEGER,
    age_years INTEGER,
    floor_number INTEGER,
    has_pool BOOLEAN DEFAULT FALSE,
    has_gym BOOLEAN DEFAULT FALSE,
    has_laundry BOOLEAN DEFAULT FALSE,
    has_security BOOLEAN DEFAULT FALSE,
    has_balcony BOOLEAN DEFAULT FALSE,
    expenses_ars FLOAT,
    price_score INTEGER,
    price_per_m2_usd FLOAT,
    first_seen_at TIMESTAMP DEFAULT NOW(),
    last_seen_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    -- Migration 002
    apto_credito BOOLEAN DEFAULT FALSE,
    -- Migration 003
    zone_score INTEGER,
    condition_score INTEGER,
    overall_score INTEGER
);

CREATE INDEX IF NOT EXISTS idx_properties_type_listing ON properties(property_type, listing_type);
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(location_id);
CREATE INDEX IF NOT EXISTS idx_properties_address_trgm ON properties USING gin(address_normalized gin_trgm_ops);

-- property_listings
CREATE TABLE IF NOT EXISTS property_listings (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id),
    source sourcetype NOT NULL,
    source_url VARCHAR(1000) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    original_title VARCHAR(500),
    original_address VARCHAR(500),
    original_price FLOAT,
    original_currency currencytype,
    image_urls TEXT[],
    raw_data JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_source_source_id UNIQUE(source, source_id)
);

-- price_history
CREATE TABLE IF NOT EXISTS price_history (
    id SERIAL PRIMARY KEY,
    property_listing_id INTEGER REFERENCES property_listings(id) NOT NULL,
    property_id INTEGER REFERENCES properties(id) NOT NULL,
    price FLOAT NOT NULL,
    currency currencytype NOT NULL,
    price_usd FLOAT,
    usd_ars_rate FLOAT,
    scraped_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_price_history_listing ON price_history(property_listing_id);
CREATE INDEX IF NOT EXISTS idx_price_history_property ON price_history(property_id);
CREATE INDEX IF NOT EXISTS idx_price_history_scraped ON price_history(scraped_at);

-- scrape_runs
CREATE TABLE IF NOT EXISTS scrape_runs (
    id SERIAL PRIMARY KEY,
    source sourcetype NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP,
    items_found INTEGER DEFAULT 0,
    items_new INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_errors INTEGER DEFAULT 0,
    error_log TEXT
);

-- zone_qualities (migration 003)
CREATE TABLE IF NOT EXISTS zone_qualities (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id) NOT NULL,
    safety_score INTEGER,
    quality_score INTEGER,
    overall_zone_score INTEGER,
    source VARCHAR(255),
    notes TEXT,
    updated_at TIMESTAMP,
    CONSTRAINT uq_zone_quality_location UNIQUE(location_id)
);

-- image_analyses (migration 003)
CREATE TABLE IF NOT EXISTS image_analyses (
    id SERIAL PRIMARY KEY,
    property_id INTEGER REFERENCES properties(id) NOT NULL,
    condition_score INTEGER,
    condition_label VARCHAR(50),
    renovation_state VARCHAR(50),
    natural_light INTEGER,
    cleanliness INTEGER,
    raw_analysis JSONB,
    images_analyzed INTEGER DEFAULT 0,
    analyzed_at TIMESTAMP,
    CONSTRAINT uq_image_analysis_property UNIQUE(property_id)
);

-- Alembic version tracking (so future migrations work)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('003')
ON CONFLICT (version_num) DO NOTHING;
