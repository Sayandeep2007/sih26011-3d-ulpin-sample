-- =====================================================================
-- SIH26011: 3D ULPIN / Vertical Property Cadastre
-- PostGIS 3D Database DDL & Automated Conflict Detection Engine
-- Standard: ISO 19152 Land Administration Domain Model (LADM)
-- Projected Coordinate Reference System: WGS 84 / UTM Zone 43N (EPSG: 32643)
-- =====================================================================

-- 1. Enable PostGIS Spatial & 3D Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS postgis_sfcgal; -- Required for 3D Solids, ST_3DIntersection & PolyhedralSurfaces

-- 2. Base 2D Ground Cadastral Parcels (Survey & Settlement Record)
CREATE TABLE cadastral_parcel_2d (
    parcel_pin VARCHAR(32) PRIMARY KEY, -- Standard 14-digit Bhu-Aadhaar PIN e.g. 'IN-KA-560001-P9402'
    state_code VARCHAR(4) NOT NULL,
    district_code VARCHAR(8) NOT NULL,
    taluk_code VARCHAR(8) NOT NULL,
    village_code VARCHAR(8) NOT NULL,
    survey_number VARCHAR(32) NOT NULL,
    total_area_sqm NUMERIC(12, 2) NOT NULL,
    geom_2d GEOMETRY(Polygon, 32643) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_parcel_2d_geom ON cadastral_parcel_2d USING GIST (geom_2d);

-- 3. Vertical 3D Volumetric Property Parcels (ISO 19152 LA_BAUnit 3D)
CREATE TABLE cadastral_volume_3d (
    ulpin_3d VARCHAR(64) PRIMARY KEY, -- e.g. 'IN-KA-560001-P9402-Z+015.5-U402-RES'
    base_parcel_pin VARCHAR(32) REFERENCES cadastral_parcel_2d(parcel_pin) ON DELETE CASCADE,
    floor_level INT NOT NULL, -- Negative for underground, 0 for ground, 1..N for upper floors
    unit_identifier VARCHAR(32) NOT NULL, -- e.g. 'U402', 'B1-PARK', 'AIR-TDR-01'
    unit_category VARCHAR(32) NOT NULL CHECK (unit_category IN ('RESIDENTIAL', 'COMMERCIAL', 'SUBTERRANEAN', 'AIR_RIGHTS', 'PUBLIC_INFRASTRUCTURE', 'COMMON_AREA')),
    z_min_msl NUMERIC(8, 2) NOT NULL, -- Orthometric elevation MSL (bottom slab)
    z_max_msl NUMERIC(8, 2) NOT NULL, -- Orthometric elevation MSL (ceiling slab)
    carpet_area_sqm NUMERIC(10, 2) NOT NULL,
    volume_m3 NUMERIC(12, 2) NOT NULL,
    owner_name VARCHAR(255) NOT NULL,
    deed_doc_number VARCHAR(64) NOT NULL,
    undivided_share_pct NUMERIC(6, 3) NOT NULL,
    is_disputed BOOLEAN DEFAULT FALSE,
    geom_3d GEOMETRY(PolyhedralSurfaceZ, 32643) NOT NULL, -- Watertight 3D solid geometry
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3D GIST Spatial Index for lightning-fast volumetric intersection queries
CREATE INDEX idx_volume_3d_geom ON cadastral_volume_3d USING GIST (geom_3d);

-- 4. Standout Feature: Spatial Boundary Dispute & Vertical Conflict Audit Log
CREATE TABLE spatial_dispute_log (
    dispute_id SERIAL PRIMARY KEY,
    primary_ulpin_3d VARCHAR(64) REFERENCES cadastral_volume_3d(ulpin_3d),
    conflicting_ulpin_3d VARCHAR(64) REFERENCES cadastral_volume_3d(ulpin_3d),
    dispute_type VARCHAR(64) NOT NULL, -- 'AIR_RIGHTS_ENCROACHMENT', 'SETBACK_VIOLATION', 'UNIT_OVERLAP'
    overlap_volume_m3 NUMERIC(10, 2) NOT NULL,
    geom_intersection_3d GEOMETRY(GeometryZ, 32643),
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved BOOLEAN DEFAULT FALSE
);

-- 5. Automated Trigger Function: Real-Time 3D Ownership Overlap Detector
CREATE OR REPLACE FUNCTION trg_check_3d_volumetric_conflict()
RETURNS TRIGGER AS $$
DECLARE
    rec RECORD;
    intersect_geom GEOMETRY;
    conflict_vol NUMERIC;
BEGIN
    -- Query all existing 3D parcels intersecting with the newly inserted/updated parcel in 3D space
    FOR rec IN 
        SELECT ulpin_3d, geom_3d, unit_category
        FROM cadastral_volume_3d
        WHERE ulpin_3d != NEW.ulpin_3d
          AND ST_3DIntersects(geom_3d, NEW.geom_3d)
    LOOP
        -- Calculate exact 3D Boolean intersection volume using SFCGAL
        intersect_geom := ST_3DIntersection(NEW.geom_3d, rec.geom_3d);
        conflict_vol := ST_Volume(intersect_geom);

        -- If intersecting volume exceeds tolerance (0.01 m3), log dispute and set warning flag
        IF conflict_vol > 0.01 THEN
            NEW.is_disputed := TRUE;

            INSERT INTO spatial_dispute_log (
                primary_ulpin_3d,
                conflicting_ulpin_3d,
                dispute_type,
                overlap_volume_m3,
                geom_intersection_3d
            ) VALUES (
                NEW.ulpin_3d,
                rec.ulpin_3d,
                CASE 
                    WHEN NEW.unit_category = 'AIR_RIGHTS' OR rec.unit_category = 'AIR_RIGHTS' THEN 'AIR_RIGHTS_ENCROACHMENT'
                    WHEN NEW.unit_category = 'SUBTERRANEAN' OR rec.unit_category = 'SUBTERRANEAN' THEN 'SUBTERRANEAN_EASEMENT_VIOLATION'
                    ELSE 'VOLUMETRIC_UNIT_OVERLAP'
                END,
                ROUND(conflict_vol, 2),
                intersect_geom
            );
        END IF;
    END LOOP;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_3d_volume_before_insert
BEFORE INSERT OR UPDATE ON cadastral_volume_3d
FOR EACH ROW
EXECUTE FUNCTION trg_check_3d_volumetric_conflict();

-- 6. High-Performance View for 3D CityGML & 3D Tiles Streaming APIs
CREATE OR REPLACE VIEW view_3d_tiles_export AS
SELECT 
    v.ulpin_3d,
    v.base_parcel_pin,
    v.floor_level,
    v.unit_identifier,
    v.unit_category,
    v.z_min_msl,
    v.z_max_msl,
    v.volume_m3,
    v.carpet_area_sqm,
    v.owner_name,
    v.deed_doc_number,
    v.is_disputed,
    p.survey_number,
    ST_AsGeoJSON(v.geom_3d) AS geojson_3d
FROM cadastral_volume_3d v
JOIN cadastral_parcel_2d p ON v.base_parcel_pin = p.parcel_pin;
