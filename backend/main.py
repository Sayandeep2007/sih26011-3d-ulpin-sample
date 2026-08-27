import os
from fastapi import FastAPI, HTTPException, Path, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from models import (
    PropertyResponse,
    ParcelResponse,
    GeoJsonFeature,
    ParcelSummaryResponse,
    LiDARAnalysisResponse,
    LiDARStrataResponse,
    LiDARMetadataResponse,
    LiDARSampleResponse,
    BuildingExtractionRequest,
    BuildingExtractionResponse,
    ConflictResult,
    ConflictMatrixResponse,
    ConflictListResponse,
    OverlapBounds,
    TopologyCheck,
    TopologyValidationResponse,
    TopologyAllPropertiesResponse
)
from db import get_db, engine
from db_models import (
    ParcelModel,
    PropertyModel,
    LidarSurveyModel,
    ConflictModel,
    TopologyValidationModel,
    TopologyCheckModel
)
from database import (
    get_all_properties,
    get_property_by_id,
    get_property_by_ulpin,
    get_all_parcels,
    get_parcel_by_id,
    get_properties_for_parcel,
    get_parcel_geometry,
    get_parcel_summary
)
from lidar_analysis import (
    PROTOTYPE_LIDAR_POINTS,
    analyze_lidar_points,
    get_lidar_strata,
    get_lidar_sample,
    generate_lidar_text_report,
    validate_and_sync_extraction
)
from conflict_engine import (
    CADASTRAL_3D_VOLUMES,
    evaluate_all_conflicts,
    get_conflicts_for_property,
    get_conflict_by_id,
    get_conflict_matrix
)
from topology_engine import (
    validate_property_topology,
    validate_all_properties_topology
)

app = FastAPI(
    title="GeoCadastre-3D Backend",
    description="FastAPI REST Backend for 3D Land & Vertical Property Cadastre (ULPIN, GIS, LiDAR, 3D Conflict Detection & Topology Validation)",
    version="Day 6 Step 7 (Production & Deployment Ready)"
)

# Configure CORS origins safely (supports wildcard or explicit origin whitelist)
cors_origins_env = os.getenv("CORS_ORIGINS", "*").strip()
if cors_origins_env == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="Root Project Status", tags=["General"])
def read_root():
    return {
        "project": "GeoCadastre-3D",
        "status": "Backend Online",
        "version": "Day 6 Step 7 (Production & Deployment Ready)"
    }


@app.get("/api/health", summary="Health Check", tags=["General"])
def health_check():
    return {
        "status": "healthy",
        "service": "GeoCadastre-3D Backend"
    }


@app.get("/api/health/db", summary="Database Persistence Health Check", tags=["General"])
def database_health_check(db: Session = Depends(get_db)):
    """
    Executes a live lightweight probe (SELECT 1) against the configured persistence backend.
    Returns the active database dialect and connection status.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "database": engine.dialect.name
        }
    except Exception as e:
        return {
            "status": "unavailable",
            "database": "unknown",
            "error": str(e)
        }


# =========================================================================
# PROPERTY & 3D ULPIN ENDPOINTS (DATABASE-BACKED)
# =========================================================================

@app.get(
    "/api/properties",
    response_model=List[PropertyResponse],
    summary="List All Cadastral Properties",
    tags=["Properties"]
)
def list_properties(db: Session = Depends(get_db)):
    """Returns a list of all cadastral property units and volumetric strata from persistence."""
    props = db.query(PropertyModel).all()
    if props:
        return [
            PropertyResponse(
                property_id=p.property_id,
                unit=p.unit,
                property_type=p.property_type,
                floor=p.floor,
                ulpin=p.ulpin,
                parcel_id=p.parcel_id,
                elevation_min_m=p.elevation_min_m,
                elevation_max_m=p.elevation_max_m,
                status=p.status,
                owner=p.owner,
                classification=p.classification,
                has_conflict=p.has_conflict,
                conflict_desc=p.conflict_desc
            ) for p in props
        ]
    return get_all_properties()


@app.get(
    "/api/properties/ulpin/{ulpin:path}",
    response_model=PropertyResponse,
    summary="Get Property by 3D ULPIN",
    tags=["Properties"]
)
def fetch_property_by_ulpin(
    ulpin: str = Path(..., description="Target 3D ULPIN string (e.g. IN-KA-560001-P9402-Z+015.5-U402)"),
    db: Session = Depends(get_db)
):
    """Searches the cadastral database by exact 3D ULPIN identity string."""
    prop = db.query(PropertyModel).filter(PropertyModel.ulpin == ulpin).first()
    if prop:
        return PropertyResponse(
            property_id=prop.property_id,
            unit=prop.unit,
            property_type=prop.property_type,
            floor=prop.floor,
            ulpin=prop.ulpin,
            parcel_id=prop.parcel_id,
            elevation_min_m=prop.elevation_min_m,
            elevation_max_m=prop.elevation_max_m,
            status=prop.status,
            owner=prop.owner,
            classification=prop.classification,
            has_conflict=prop.has_conflict,
            conflict_desc=prop.conflict_desc
        )
    mem_prop = get_property_by_ulpin(ulpin)
    if not mem_prop:
        raise HTTPException(
            status_code=404,
            detail=f"Property with ULPIN '{ulpin}' not found"
        )
    return mem_prop


@app.get(
    "/api/properties/{property_id}",
    response_model=PropertyResponse,
    summary="Get Property by ID",
    tags=["Properties"]
)
def fetch_property_by_id(
    property_id: str = Path(..., description="Property identifier (e.g. U401, U402, ground-commercial, b1, air-rights)"),
    db: Session = Depends(get_db)
):
    """Returns a single cadastral property record by its identifier from persistence."""
    prop = db.query(PropertyModel).filter(
        (func.lower(PropertyModel.property_id) == property_id.lower()) | 
        (PropertyModel.property_id == property_id)
    ).first()
    if prop:
        return PropertyResponse(
            property_id=prop.property_id,
            unit=prop.unit,
            property_type=prop.property_type,
            floor=prop.floor,
            ulpin=prop.ulpin,
            parcel_id=prop.parcel_id,
            elevation_min_m=prop.elevation_min_m,
            elevation_max_m=prop.elevation_max_m,
            status=prop.status,
            owner=prop.owner,
            classification=prop.classification,
            has_conflict=prop.has_conflict,
            conflict_desc=prop.conflict_desc
        )
    mem_prop = get_property_by_id(property_id)
    if not mem_prop:
        raise HTTPException(
            status_code=404,
            detail="Property not found"
        )
    return mem_prop


# =========================================================================
# PARCEL & GIS ENDPOINTS (DATABASE-BACKED)
# =========================================================================

@app.get(
    "/api/parcels",
    response_model=List[ParcelResponse],
    summary="List All Base Cadastral Parcels",
    tags=["Parcels / GIS"]
)
def list_parcels(db: Session = Depends(get_db)):
    """Returns all available base 2D cadastral land parcels from persistence."""
    parcels = db.query(ParcelModel).all()
    if parcels:
        return [
            ParcelResponse(
                parcel_id=p.parcel_id,
                survey_number=p.survey_number,
                location_name=p.location_name,
                ulpin_base=p.ulpin_base,
                coordinate_reference=p.coordinate_reference,
                min_x=p.min_x,
                max_x=p.max_x,
                min_z=p.min_z,
                max_z=p.max_z,
                width_m=p.width_m,
                depth_m=p.depth_m,
                area_m2=p.area_m2,
                elevation_min_m=p.elevation_min_m,
                elevation_max_m=p.elevation_max_m,
                status=p.status,
                data_classification=p.data_classification,
                gnss_cors_note=p.gnss_cors_note
            ) for p in parcels
        ]
    return get_all_parcels()


@app.get(
    "/api/parcels/{parcel_id}",
    response_model=ParcelResponse,
    summary="Get Base Parcel Details",
    tags=["Parcels / GIS"]
)
def fetch_parcel_by_id(
    parcel_id: str = Path(..., description="Base parcel identifier (e.g. P9402)"),
    db: Session = Depends(get_db)
):
    """Returns the base cadastral parcel record including survey number and 2D footprint extents from persistence."""
    parcel = db.query(ParcelModel).filter(
        (func.lower(ParcelModel.parcel_id) == parcel_id.lower()) |
        (ParcelModel.parcel_id == parcel_id)
    ).first()
    if parcel:
        return ParcelResponse(
            parcel_id=parcel.parcel_id,
            survey_number=parcel.survey_number,
            location_name=parcel.location_name,
            ulpin_base=parcel.ulpin_base,
            coordinate_reference=parcel.coordinate_reference,
            min_x=parcel.min_x,
            max_x=parcel.max_x,
            min_z=parcel.min_z,
            max_z=parcel.max_z,
            width_m=parcel.width_m,
            depth_m=parcel.depth_m,
            area_m2=parcel.area_m2,
            elevation_min_m=parcel.elevation_min_m,
            elevation_max_m=parcel.elevation_max_m,
            status=parcel.status,
            data_classification=parcel.data_classification,
            gnss_cors_note=parcel.gnss_cors_note
        )
    mem_parcel = get_parcel_by_id(parcel_id)
    if not mem_parcel:
        raise HTTPException(
            status_code=404,
            detail="Parcel not found"
        )
    return mem_parcel


@app.get(
    "/api/parcels/{parcel_id}/geometry",
    response_model=GeoJsonFeature,
    summary="Get Parcel 2D Boundary Geometry (GeoJSON)",
    tags=["Parcels / GIS"]
)
def fetch_parcel_geometry(
    parcel_id: str = Path(..., description="Base parcel identifier (e.g. P9402)"),
    db: Session = Depends(get_db)
):
    """Returns the parcel 2D boundary polygon in a GeoJSON-compatible Feature structure using local X/Z Cartesian coordinates."""
    parcel = db.query(ParcelModel).filter(
        (func.lower(ParcelModel.parcel_id) == parcel_id.lower()) |
        (ParcelModel.parcel_id == parcel_id)
    ).first()
    if parcel:
        coords = [
            [
                [parcel.min_x, parcel.min_z],
                [parcel.max_x, parcel.min_z],
                [parcel.max_x, parcel.max_z],
                [parcel.min_x, parcel.max_z],
                [parcel.min_x, parcel.min_z]
            ]
        ]
        return GeoJsonFeature(
            type="Feature",
            properties={
                "parcel_id": parcel.parcel_id,
                "survey_number": parcel.survey_number,
                "ulpin_base": parcel.ulpin_base,
                "coordinate_reference": "LOCAL_XZ_CADASTRAL",
                "coordinate_note": "Local X/Z Cartesian offsets in meters from ground origin. Not WGS84 degrees.",
                "area_m2": parcel.area_m2,
                "data_classification": parcel.data_classification,
                "gnss_cors_note": parcel.gnss_cors_note
            },
            geometry={
                "type": "Polygon",
                "coordinates": coords
            }
        )
    mem_geom = get_parcel_geometry(parcel_id)
    if not mem_geom:
        raise HTTPException(
            status_code=404,
            detail="Parcel not found"
        )
    return mem_geom


@app.get(
    "/api/parcels/{parcel_id}/properties",
    response_model=List[PropertyResponse],
    summary="Get All Properties Associated with Parcel",
    tags=["Parcels / GIS"]
)
def fetch_parcel_properties(
    parcel_id: str = Path(..., description="Base parcel identifier (e.g. P9402)"),
    db: Session = Depends(get_db)
):
    """Establishes the Parcel ➔ Property vertical relationship by returning all 3D volumetric units registered under this base parcel."""
    parcel = db.query(ParcelModel).filter(
        (func.lower(ParcelModel.parcel_id) == parcel_id.lower()) |
        (ParcelModel.parcel_id == parcel_id)
    ).first()
    if parcel:
        props = db.query(PropertyModel).filter(
            (func.lower(PropertyModel.parcel_id) == parcel_id.lower()) |
            (PropertyModel.parcel_id == parcel.parcel_id)
        ).all()
        return [
            PropertyResponse(
                property_id=p.property_id,
                unit=p.unit,
                property_type=p.property_type,
                floor=p.floor,
                ulpin=p.ulpin,
                parcel_id=p.parcel_id,
                elevation_min_m=p.elevation_min_m,
                elevation_max_m=p.elevation_max_m,
                status=p.status,
                owner=p.owner,
                classification=p.classification,
                has_conflict=p.has_conflict,
                conflict_desc=p.conflict_desc
            ) for p in props
        ]
    mem_props = get_properties_for_parcel(parcel_id)
    if mem_props is None:
        raise HTTPException(
            status_code=404,
            detail="Parcel not found"
        )
    return mem_props


@app.get(
    "/api/parcels/{parcel_id}/summary",
    response_model=ParcelSummaryResponse,
    summary="Get Compact Cadastral Parcel Summary",
    tags=["Parcels / GIS"]
)
def fetch_parcel_summary(
    parcel_id: str = Path(..., description="Base parcel identifier (e.g. P9402)"),
    db: Session = Depends(get_db)
):
    """Returns an integrated summary combining 2D parcel boundary metrics with live associated 3D property volume counts."""
    parcel = db.query(ParcelModel).filter(
        (func.lower(ParcelModel.parcel_id) == parcel_id.lower()) |
        (ParcelModel.parcel_id == parcel_id)
    ).first()
    if parcel:
        props = db.query(PropertyModel).filter(
            (func.lower(PropertyModel.parcel_id) == parcel_id.lower()) |
            (PropertyModel.parcel_id == parcel.parcel_id)
        ).all()
        prop_ids = [p.property_id for p in props]
        return ParcelSummaryResponse(
            parcel_id=parcel.parcel_id,
            survey_number=parcel.survey_number,
            base_ulpin=parcel.ulpin_base,
            area_m2=parcel.area_m2,
            footprint=f"[{parcel.min_x:.1f}, {parcel.max_x:.1f}]m × [{parcel.min_z:.1f}, {parcel.max_z:.1f}]m (Width: {parcel.width_m:.1f}m, Depth: {parcel.depth_m:.1f}m)",
            elevation_range=f"{parcel.elevation_min_m:+.1f}m to {parcel.elevation_max_m:+.1f}m MSL",
            associated_property_count=len(props),
            associated_property_ids=prop_ids,
            data_classification=parcel.data_classification
        )
    mem_summary = get_parcel_summary(parcel_id)
    if not mem_summary:
        raise HTTPException(
            status_code=404,
            detail="Parcel not found"
        )
    return mem_summary


# =========================================================================
# LIDAR ANALYSIS ENDPOINTS
# =========================================================================

@app.get(
    "/api/lidar/analysis",
    response_model=LiDARAnalysisResponse,
    summary="Compute Full LiDAR Point Cloud Analysis",
    tags=["LiDAR Analysis"]
)
def fetch_lidar_analysis():
    """Executes live mathematical analysis over the 6,000-point LiDAR survey dataset and computes bounding extents, volumes, and vertical strata."""
    try:
        return analyze_lidar_points(PROTOTYPE_LIDAR_POINTS)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LiDAR analysis computation failed: {str(e)}")


@app.get(
    "/api/lidar/strata",
    response_model=LiDARStrataResponse,
    summary="Get Vertical Elevation Strata",
    tags=["LiDAR Analysis"]
)
def fetch_lidar_strata():
    """Returns the rule-based geometric vertical segmentation breakdown across all 8 prototype elevation strata."""
    return get_lidar_strata()


@app.get(
    "/api/lidar/metadata",
    response_model=LiDARMetadataResponse,
    summary="Get LiDAR Dataset Metadata",
    tags=["LiDAR Analysis"]
)
def fetch_lidar_metadata(db: Session = Depends(get_db)):
    """Returns project-level metadata, coordinate reference information, and data integrity specifications for the LiDAR survey dataset from persistence."""
    survey = db.query(LidarSurveyModel).first()
    if survey:
        return LiDARMetadataResponse(
            project="GeoCadastre-3D",
            survey_classification=survey.data_classification,
            point_count=survey.total_points,
            coordinate_reference="Local Cadastral Ground Origin (MSL Datum +0.00m) - LOCAL_XYZ",
            data_source_type=survey.data_source_type,
            processing_classification="Rule-Based Geometric Stratification",
            prototype_status="Development Prototype TLS Dataset",
            ai_ml_disclaimer="Deterministic geometric vertical slicing. No AI/ML hallucination."
        )
    return LiDARMetadataResponse()


@app.get(
    "/api/lidar/sample",
    response_model=LiDARSampleResponse,
    summary="Get Diagnostic Sample Points",
    tags=["LiDAR Analysis"]
)
def fetch_lidar_sample():
    """Returns a diagnostic 10-point sample from the survey cloud without returning the entire 6,000-point dataset."""
    return get_lidar_sample(limit=10)


@app.get(
    "/api/lidar/report",
    response_class=PlainTextResponse,
    summary="Generate Plain-Text LiDAR Survey Report",
    tags=["LiDAR Analysis"]
)
def fetch_lidar_report():
    """Generates a downloadable plain-text LiDAR survey report computed dynamically from the live analysis engine."""
    return generate_lidar_text_report()


@app.post(
    "/api/lidar/extract",
    response_model=BuildingExtractionResponse,
    summary="Validate and Synchronize Building & Floor Extraction",
    tags=["LiDAR Analysis"]
)
def sync_building_extraction(request: Optional[BuildingExtractionRequest] = None):
    """Receives and validates geometric floor extraction results against authoritative LiDAR survey stratification rules."""
    try:
        return validate_and_sync_extraction(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Building extraction synchronization failed: {str(e)}")


@app.get(
    "/api/lidar/extract",
    response_model=BuildingExtractionResponse,
    summary="Get Synchronized Building & Floor Extraction",
    tags=["LiDAR Analysis"]
)
def get_building_extraction():
    """Returns the validated building and floor extraction breakdown across all 8 architectural strata."""
    try:
        return validate_and_sync_extraction(None)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fetching building extraction failed: {str(e)}")


# =========================================================================
# 3D SPATIAL CONFLICT DETECTION ENDPOINTS (DATABASE-BACKED)
# =========================================================================

@app.get(
    "/api/conflicts",
    response_model=ConflictListResponse,
    summary="List All Detected 3D Spatial Conflicts",
    tags=["3D Conflict Detection"]
)
def list_all_conflicts(db: Session = Depends(get_db)):
    """Performs dynamic pairwise 3D AABB intersection testing across all registered property volumes and returns active boundary disputes."""
    db_conflicts = db.query(ConflictModel).all()
    if db_conflicts:
        conflict_results = [
            ConflictResult(
                conflict_id=c.conflict_id,
                property_a=c.property_a,
                property_a_name=c.property_a_name,
                property_b=c.property_b,
                property_b_name=c.property_b_name,
                overlap_exists=c.overlap_exists,
                overlap_volume_m3=c.overlap_volume_m3,
                conflict_type=c.conflict_type,
                severity=c.severity,
                status=c.status,
                overlap_bounds=OverlapBounds(
                    min_x=c.overlap_min_x,
                    max_x=c.overlap_max_x,
                    min_y=c.overlap_min_y,
                    max_y=c.overlap_max_y,
                    min_z=c.overlap_min_z,
                    max_z=c.overlap_max_z,
                    width_m=c.overlap_width_m,
                    height_m=c.overlap_height_m,
                    depth_m=c.overlap_depth_m
                ) if c.overlap_exists else None,
                processing_method=c.processing_method,
                data_classification=c.data_classification
            ) for c in db_conflicts
        ]
        total_vol = sum(c.overlap_volume_m3 for c in conflict_results)
        return ConflictListResponse(
            total_conflicts=len(conflict_results),
            total_disputed_volume_m3=round(total_vol, 2),
            processing_method="Rule-Based 3D AABB Intersection",
            conflicts=conflict_results
        )
    active_conflicts = evaluate_all_conflicts()
    total_vol = sum(c.overlap_volume_m3 for c in active_conflicts)
    return ConflictListResponse(
        total_conflicts=len(active_conflicts),
        total_disputed_volume_m3=round(total_vol, 2),
        processing_method="Rule-Based 3D AABB Intersection",
        conflicts=active_conflicts
    )


@app.get(
    "/api/conflicts/matrix",
    response_model=ConflictMatrixResponse,
    summary="Get Pairwise 3D Conflict Matrix",
    tags=["3D Conflict Detection"]
)
def fetch_conflict_matrix():
    """Evaluates every unique unordered pair of 3D cadastral volumes and returns the complete pairwise spatial collision matrix."""
    return get_conflict_matrix()


@app.get(
    "/api/conflicts/property/{property_id}",
    response_model=List[ConflictResult],
    summary="Get Conflicts Involving a Specific Property",
    tags=["3D Conflict Detection"]
)
def fetch_conflicts_for_property(
    property_id: str = Path(..., description="Property identifier (e.g. U401, U402, ground-commercial, b1, air-rights)"),
    db: Session = Depends(get_db)
):
    """Returns all 3D spatial boundary conflicts associated with the specified property from persistence."""
    prop_exists = (
        db.query(PropertyModel).filter(
            (func.lower(PropertyModel.property_id) == property_id.lower()) |
            (PropertyModel.property_id == property_id)
        ).first() is not None or 
        property_id.lower() in CADASTRAL_3D_VOLUMES or 
        property_id in ("municipal-setback", "U401", "U402", "ground-commercial", "b1", "air-rights")
    )

    if not prop_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Property '{property_id}' not found in 3D spatial volume registry"
        )

    db_conflicts = db.query(ConflictModel).filter(
        (func.lower(ConflictModel.property_a) == property_id.lower()) |
        (func.lower(ConflictModel.property_b) == property_id.lower()) |
        (ConflictModel.property_a == property_id) |
        (ConflictModel.property_b == property_id)
    ).all()

    if db_conflicts:
        return [
            ConflictResult(
                conflict_id=c.conflict_id,
                property_a=c.property_a,
                property_a_name=c.property_a_name,
                property_b=c.property_b,
                property_b_name=c.property_b_name,
                overlap_exists=c.overlap_exists,
                overlap_volume_m3=c.overlap_volume_m3,
                conflict_type=c.conflict_type,
                severity=c.severity,
                status=c.status,
                overlap_bounds=OverlapBounds(
                    min_x=c.overlap_min_x,
                    max_x=c.overlap_max_x,
                    min_y=c.overlap_min_y,
                    max_y=c.overlap_max_y,
                    min_z=c.overlap_min_z,
                    max_z=c.overlap_max_z,
                    width_m=c.overlap_width_m,
                    height_m=c.overlap_height_m,
                    depth_m=c.overlap_depth_m
                ) if c.overlap_exists else None,
                processing_method=c.processing_method,
                data_classification=c.data_classification
            ) for c in db_conflicts
        ]
    
    mem_results = get_conflicts_for_property(property_id)
    return mem_results if mem_results is not None else []


@app.get(
    "/api/conflicts/{conflict_id}",
    response_model=ConflictResult,
    summary="Get Specific Conflict Details by ID",
    tags=["3D Conflict Detection"]
)
def fetch_conflict_by_id(
    conflict_id: str = Path(..., description="Unique conflict identifier (e.g. CONF-U401-MUNICIPAL-SETBACK-01)"),
    db: Session = Depends(get_db)
):
    """Returns granular mathematical intersection details, coordinates, and classification for a specific conflict from persistence."""
    c = db.query(ConflictModel).filter(
        (func.lower(ConflictModel.conflict_id) == conflict_id.lower()) |
        (ConflictModel.conflict_id == conflict_id)
    ).first()
    if c:
        return ConflictResult(
            conflict_id=c.conflict_id,
            property_a=c.property_a,
            property_a_name=c.property_a_name,
            property_b=c.property_b,
            property_b_name=c.property_b_name,
            overlap_exists=c.overlap_exists,
            overlap_volume_m3=c.overlap_volume_m3,
            conflict_type=c.conflict_type,
            severity=c.severity,
            status=c.status,
            overlap_bounds=OverlapBounds(
                min_x=c.overlap_min_x,
                max_x=c.overlap_max_x,
                min_y=c.overlap_min_y,
                max_y=c.overlap_max_y,
                min_z=c.overlap_min_z,
                max_z=c.overlap_max_z,
                width_m=c.overlap_width_m,
                height_m=c.overlap_height_m,
                depth_m=c.overlap_depth_m
            ) if c.overlap_exists else None,
            processing_method=c.processing_method,
            data_classification=c.data_classification
        )
    mem_c = get_conflict_by_id(conflict_id)
    if not mem_c:
        raise HTTPException(
            status_code=404,
            detail=f"Conflict with ID '{conflict_id}' not found"
        )
    return mem_c


# =========================================================================
# 3D CADASTRAL TOPOLOGY VALIDATION ENDPOINTS (DATABASE-BACKED)
# =========================================================================

@app.get(
    "/api/topology/validate",
    response_model=TopologyAllPropertiesResponse,
    summary="Validate 3D Topology for All Registered Properties",
    tags=["3D Topology Validation"]
)
def validate_all_topology(db: Session = Depends(get_db)):
    """Evaluates all registered 3D property volumes against the 4 core cadastral topological rules from persistence."""
    db_validations = db.query(TopologyValidationModel).all()
    if db_validations:
        vals = []
        comp_count = 0
        non_comp_count = 0
        for v in db_validations:
            if v.overall_status == "PASS":
                comp_count += 1
            else:
                non_comp_count += 1
            
            chks = [
                TopologyCheck(
                    check_id=ch.check_id,
                    check_name=ch.check_name,
                    status=ch.status,
                    description=ch.description,
                    property_id=ch.property_id,
                    related_property_id=ch.related_property_id,
                    measured_value=ch.measured_value,
                    expected_condition=ch.expected_condition,
                    processing_method=ch.processing_method,
                    data_classification=ch.data_classification
                ) for ch in v.checks
            ]
            vals.append(
                TopologyValidationResponse(
                    validation_id=v.validation_id,
                    property_id=v.property_id,
                    property_name=v.property_name,
                    overall_status=v.overall_status,
                    passed_check_count=v.passed_check_count,
                    failed_check_count=v.failed_check_count,
                    checks=chks,
                    processing_method=v.processing_method,
                    data_classification=v.data_classification
                )
            )
        return TopologyAllPropertiesResponse(
            processing_method="Rule-Based 3D Cadastral Topology Validation",
            total_properties_validated=len(vals),
            compliant_properties_count=comp_count,
            non_compliant_properties_count=non_comp_count,
            validations=vals
        )
    return validate_all_properties_topology()


@app.get(
    "/api/topology/validate/{property_id}",
    response_model=TopologyValidationResponse,
    summary="Validate 3D Topology for Specific Property",
    tags=["3D Topology Validation"]
)
def validate_property_topology_endpoint(
    property_id: str = Path(..., description="Property identifier (e.g. U401, U402, ground-commercial, b1, air-rights)"),
    db: Session = Depends(get_db)
):
    """Evaluates the 4 topological rules (NON_OVERLAP, FOOTPRINT_CONSISTENCY, VERTICAL_CONTINUITY, SUBTERRANEAN_BUFFER) for a single property from persistence."""
    v = db.query(TopologyValidationModel).filter(
        (func.lower(TopologyValidationModel.property_id) == property_id.lower()) |
        (TopologyValidationModel.property_id == property_id)
    ).first()
    if v:
        chks = [
            TopologyCheck(
                check_id=ch.check_id,
                check_name=ch.check_name,
                status=ch.status,
                description=ch.description,
                property_id=ch.property_id,
                related_property_id=ch.related_property_id,
                measured_value=ch.measured_value,
                expected_condition=ch.expected_condition,
                processing_method=ch.processing_method,
                data_classification=ch.data_classification
            ) for ch in v.checks
        ]
        return TopologyValidationResponse(
            validation_id=v.validation_id,
            property_id=v.property_id,
            property_name=v.property_name,
            overall_status=v.overall_status,
            passed_check_count=v.passed_check_count,
            failed_check_count=v.failed_check_count,
            checks=chks,
            processing_method=v.processing_method,
            data_classification=v.data_classification
        )
    mem_res = validate_property_topology(property_id)
    if not mem_res:
        raise HTTPException(
            status_code=404,
            detail=f"Property '{property_id}' not found in 3D cadastral topology registry"
        )
    return mem_res


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
