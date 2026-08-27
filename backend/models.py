from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


# =========================================================================
# PROPERTY & 3D ULPIN MODELS
# =========================================================================

class PropertyResponse(BaseModel):
    property_id: str = Field(..., description="Unique prototype property identifier (e.g. U401, U402, ground-commercial)")
    unit: str = Field(..., description="Unit or parcel title")
    property_type: str = Field(..., description="Cadastral classification (e.g. Residential Apartment, Commercial)")
    floor: Optional[int] = Field(None, description="Physical floor level relative to ground datum")
    ulpin: str = Field(..., description="3D Unique Land Parcel Identification Number")
    parcel_id: str = Field(..., description="Base 2D parcel PIN")
    elevation_min_m: float = Field(..., description="Lower vertical boundary in meters (MSL Datum)")
    elevation_max_m: float = Field(..., description="Upper vertical boundary in meters (MSL Datum)")
    status: str = Field("REGISTERED", description="Cadastral status (REGISTERED, DISPUTED, PROTOTYPE)")
    owner: str = Field("Prototype Owner (Sample Data)", description="Authoritative deed titleholder (Prototype/Sample)")
    classification: str = Field("Prototype Cadastral Record", description="Record integrity level")
    has_conflict: bool = Field(False, description="Whether an active 3D boundary overlap conflict exists")
    conflict_desc: Optional[str] = Field(None, description="Dispute explanation if has_conflict is True")


# =========================================================================
# PARCEL & GIS MODELS
# =========================================================================

class ParcelResponse(BaseModel):
    parcel_id: str = Field(..., description="Unique 2D base parcel identifier (e.g. P9402)")
    survey_number: str = Field(..., description="Revenue survey/subdivision identifier (e.g. 42/1)")
    location_name: str = Field(..., description="Descriptive cadastral location and revenue ward")
    ulpin_base: str = Field(..., description="Authoritative 2D Base ULPIN identifier")
    coordinate_reference: str = Field(..., description="Coordinate system metadata (Local X/Z Cadastral Ground Origin)")
    min_x: float = Field(..., description="Minimum horizontal X boundary (meters)")
    max_x: float = Field(..., description="Maximum horizontal X boundary (meters)")
    min_z: float = Field(..., description="Minimum horizontal Z boundary (meters)")
    max_z: float = Field(..., description="Maximum horizontal Z boundary (meters)")
    width_m: float = Field(..., description="Parcel total horizontal width (meters)")
    depth_m: float = Field(..., description="Parcel total horizontal depth (meters)")
    area_m2: float = Field(..., description="Base parcel 2D surface footprint area (square meters)")
    elevation_min_m: float = Field(..., description="Subterranean foundation clearance limit (MSL Datum)")
    elevation_max_m: float = Field(..., description="Airspace vertical envelope ceiling (MSL Datum)")
    status: str = Field("REGISTERED", description="Cadastral registration state")
    data_classification: str = Field("Prototype Cadastral Data", description="Data integrity classification")
    gnss_cors_note: str = Field("GNSS/CORS integration point: prototype", description="Geodetic reference note")


class GeoJsonFeature(BaseModel):
    type: str = Field("Feature", description="GeoJSON object type")
    properties: Dict[str, Any] = Field(..., description="Parcel metadata and coordinate reference attributes")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON 2D Polygon geometry representing local X/Z boundaries")


class ParcelSummaryResponse(BaseModel):
    parcel_id: str = Field(..., description="Base parcel ID")
    survey_number: str = Field(..., description="Survey/Subdivision number")
    base_ulpin: str = Field(..., description="Authoritative Base 2D ULPIN")
    area_m2: float = Field(..., description="2D Surface Footprint Area in m²")
    footprint: str = Field(..., description="Horizontal boundary extent string")
    elevation_range: str = Field(..., description="Vertical cadastral envelope span")
    associated_property_count: int = Field(..., description="Number of associated 3D volumetric properties")
    associated_property_ids: List[str] = Field(..., description="List of associated property identifiers")
    data_classification: str = Field("Prototype Cadastral Data", description="Data integrity status")


# =========================================================================
# LIDAR ANALYSIS MODELS
# =========================================================================

class LiDARPoint(BaseModel):
    id: int = Field(..., description="Point index")
    x: float = Field(..., description="X coordinate in meters")
    y: float = Field(..., description="Y (elevation) coordinate in meters (MSL Datum)")
    z: float = Field(..., description="Z coordinate in meters")


class LiDARStratum(BaseModel):
    name: str = Field(..., description="Elevation stratum title")
    elevation_min_m: float = Field(..., description="Lower stratum elevation bound in meters")
    elevation_max_m: float = Field(..., description="Upper stratum elevation bound in meters")
    point_count: int = Field(..., description="Number of LiDAR survey points within this elevation stratum")
    percentage: float = Field(..., description="Percentage of total point cloud")
    processing_method: str = Field("Rule-Based Geometric Vertical Segmentation", description="Methodology used")


class LiDARStrataResponse(BaseModel):
    project: str = Field("GeoCadastre-3D", description="Project title")
    survey_classification: str = Field("Prototype Survey TLS", description="Survey data classification")
    total_points: int = Field(..., description="Total points analyzed")
    processing_method: str = Field("Rule-Based Geometric Vertical Segmentation", description="Methodology description")
    strata: List[LiDARStratum] = Field(..., description="Calculated vertical elevation strata")


class LiDARAnalysisResponse(BaseModel):
    project: str = Field("GeoCadastre-3D", description="Project title")
    survey_classification: str = Field("Prototype Survey TLS", description="Survey data classification")
    coordinate_reference: str = Field("Local Cadastral Ground Origin (MSL Datum +0.00m) - LOCAL_XYZ", description="Reference frame")
    total_points: int = Field(..., description="Total analyzed point count")
    min_x: float = Field(..., description="Minimum horizontal X coordinate")
    max_x: float = Field(..., description="Maximum horizontal X coordinate")
    min_y: float = Field(..., description="Minimum vertical elevation Y (MSL Datum)")
    max_y: float = Field(..., description="Maximum vertical elevation Y (MSL Datum)")
    min_z: float = Field(..., description="Minimum horizontal Z coordinate")
    max_z: float = Field(..., description="Maximum horizontal Z coordinate")
    span_x: float = Field(..., description="Horizontal X span in meters")
    vertical_span: float = Field(..., description="Total vertical elevation range in meters")
    span_z: float = Field(..., description="Horizontal Z span in meters")
    bounding_extent: str = Field(..., description="3D Bounding Extent formatted string (W × H × D)")
    enclosure_volume_m3: float = Field(..., description="Calculated 3D bounding enclosure volume in cubic meters")
    processing_method: str = Field("Rule-Based Geometric Analysis", description="Analysis methodology")
    data_integrity_note: str = Field("Prototype survey point cloud. Calculated dynamically from 6,000 spatial survey points.", description="Data integrity declaration")
    strata: List[LiDARStratum] = Field(..., description="Vertical elevation strata breakdown")


class LiDARMetadataResponse(BaseModel):
    project: str = Field("GeoCadastre-3D", description="Project title")
    survey_classification: str = Field("Prototype Survey TLS", description="Survey data classification")
    point_count: int = Field(6000, description="Point cloud dataset size")
    coordinate_reference: str = Field("Local Cadastral Ground Origin (MSL Datum +0.00m) - LOCAL_XYZ", description="Reference datum")
    data_source_type: str = Field("Simulated Terrestrial Laser Scanner (TLS)", description="Sensor platform")
    processing_classification: str = Field("Rule-Based Geometric Analysis", description="Processing category")
    prototype_status: str = Field("Active Prototype Dataset", description="Lifecycle state")
    ai_ml_disclaimer: str = Field("Prototype geometric segmentation. AI/ML semantic extraction is a future processing stage.", description="AI/ML transparency notice")


class LiDARSampleResponse(BaseModel):
    sample_type: str = Field("Diagnostic sample — not complete point cloud", description="Sample scope note")
    sample_size: int = Field(10, description="Number of points in sample")
    total_point_cloud_size: int = Field(6000, description="Total size of underlying point cloud")
    points: List[LiDARPoint] = Field(..., description="First 10 diagnostic points")


class StratumExtractionInput(BaseModel):
    name: str = Field(..., description="Name of physical stratum (e.g. Subterranean, Floor 1)")
    elevation_min_m: float = Field(..., description="Lower stratum elevation bound in meters")
    elevation_max_m: float = Field(..., description="Upper stratum elevation bound in meters")
    point_count: int = Field(..., description="Number of LiDAR survey points within this elevation stratum")
    percentage: Optional[float] = Field(None, description="Percentage of total point cloud")


class BuildingExtractionRequest(BaseModel):
    project: str = Field("GeoCadastre-3D", description="Project identifier")
    total_points: int = Field(6000, description="Total LiDAR points extracted")
    extraction_method: str = Field("Rule-Based Geometric Vertical Segmentation", description="Methodology used")
    strata: Optional[Dict[str, Any]] = Field(None, description="Extracted strata mapped by key")


class BuildingExtractionResponse(BaseModel):
    project: str = Field("GeoCadastre-3D", description="Project identifier")
    status: str = Field("SYNCHRONIZED", description="Synchronization status")
    message: str = Field("Building & Floor Extraction validated and synchronized successfully.", description="Status message")
    total_points: int = Field(..., description="Validated total point count")
    strata_count: int = Field(8, description="Number of building strata extracted")
    extraction_method: str = Field("Rule-Based Geometric Vertical Segmentation", description="Methodology used")
    data_classification: str = Field("Prototype Cadastral Data", description="Data integrity status")
    strata: List[LiDARStratum] = Field(..., description="Validated vertical elevation strata")


# =========================================================================
# 3D SPATIAL CONFLICT MODELS
# =========================================================================

class BoundingBox3D(BaseModel):
    min_x: float = Field(..., description="Minimum X coordinate in meters")
    max_x: float = Field(..., description="Maximum X coordinate in meters")
    min_y: float = Field(..., description="Minimum elevation Y in meters (MSL Datum)")
    max_y: float = Field(..., description="Maximum elevation Y in meters (MSL Datum)")
    min_z: float = Field(..., description="Minimum Z coordinate in meters")
    max_z: float = Field(..., description="Maximum Z coordinate in meters")


class OverlapBounds(BaseModel):
    min_x: float = Field(..., description="Overlap minimum X boundary")
    max_x: float = Field(..., description="Overlap maximum X boundary")
    min_y: float = Field(..., description="Overlap minimum Y elevation")
    max_y: float = Field(..., description="Overlap maximum Y elevation")
    min_z: float = Field(..., description="Overlap minimum Z boundary")
    max_z: float = Field(..., description="Overlap maximum Z boundary")
    width_m: float = Field(..., description="Overlap width along X axis")
    height_m: float = Field(..., description="Overlap height along Y elevation axis")
    depth_m: float = Field(..., description="Overlap depth along Z axis")


class ConflictResult(BaseModel):
    conflict_id: str = Field(..., description="Unique spatial conflict ID (e.g. CONF-U401-SETBACK-01)")
    property_a: str = Field(..., description="Primary property ID (e.g. U401)")
    property_b: str = Field(..., description="Encroached property or airspace parcel ID (e.g. municipal-setback)")
    property_a_name: str = Field(..., description="Descriptive title of property A")
    property_b_name: str = Field(..., description="Descriptive title of property B")
    overlap_exists: bool = Field(..., description="Whether volumetric overlap > 0.001 m³")
    overlap_volume_m3: float = Field(..., description="Mathematically calculated overlapping volume in m³")
    overlap_bounds: Optional[OverlapBounds] = Field(None, description="Spatial coordinates and dimensions of overlapping prism")
    conflict_type: str = Field("3D Boundary / Volumetric Overlap", description="Spatial conflict classification")
    severity: str = Field("HIGH", description="Conflict severity level (HIGH, MEDIUM, LOW, NONE)")
    status: str = Field("DISPUTED", description="Cadastral dispute status (DISPUTED, NO_CONFLICT)")
    processing_method: str = Field("Rule-Based 3D AABB Intersection", description="Analytical methodology used")
    data_classification: str = Field("Prototype Cadastral Data", description="Data integrity status")


class ConflictPairSummary(BaseModel):
    property_a: str = Field(..., description="Property A ID")
    property_b: str = Field(..., description="Property B ID")
    overlap_exists: bool = Field(..., description="Whether overlap exists")
    overlap_volume_m3: float = Field(..., description="Calculated overlap volume in m³")
    status: str = Field(..., description="Cadastral relationship status")


class ConflictMatrixResponse(BaseModel):
    processing_method: str = Field("Rule-Based 3D AABB Intersection", description="Algorithm applied")
    evaluated_properties: List[str] = Field(..., description="List of 3D volume identifiers evaluated")
    total_pairs_evaluated: int = Field(..., description="Number of unique pairwise combinations tested")
    conflicts_detected_count: int = Field(..., description="Count of detected spatial conflicts")
    total_disputed_volume_m3: float = Field(..., description="Sum of all overlapping volumes in m³")
    matrix: List[ConflictPairSummary] = Field(..., description="Pairwise intersection evaluation list")


class ConflictListResponse(BaseModel):
    total_conflicts: int = Field(..., description="Total active spatial conflicts detected")
    total_disputed_volume_m3: float = Field(..., description="Sum of disputed volumes in cubic meters")
    processing_method: str = Field("Rule-Based 3D AABB Intersection", description="Algorithm used")
    conflicts: List[ConflictResult] = Field(..., description="List of active conflict details")


# =========================================================================
# 3D CADASTRAL TOPOLOGY VALIDATION MODELS
# =========================================================================

class TopologyCheck(BaseModel):
    check_id: str = Field(..., description="Rule check code (e.g. TOP-01, TOP-02, TOP-03, TOP-04)")
    check_name: str = Field(..., description="Topology rule name (e.g. NON_OVERLAP, FOOTPRINT_CONSISTENCY, VERTICAL_CONTINUITY, SUBTERRANEAN_BUFFER)")
    status: str = Field(..., description="Verification status (PASS, FAIL, WARNING)")
    description: str = Field(..., description="Rule verification description and diagnosis")
    property_id: str = Field(..., description="Target property ID")
    related_property_id: Optional[str] = Field(None, description="Related or intersecting property/parcel ID if applicable")
    measured_value: str = Field(..., description="Measured spatial parameter value")
    expected_condition: str = Field(..., description="Mathematical criterion for topological validity")
    processing_method: str = Field("Rule-Based 3D Cadastral Topology Validation", description="Validation engine label")
    data_classification: str = Field("Prototype Cadastral Data", description="Data classification")


class TopologyValidationResponse(BaseModel):
    validation_id: str = Field(..., description="Unique validation transaction ID")
    property_id: str = Field(..., description="Validated property identifier")
    property_name: str = Field(..., description="Property descriptive title")
    overall_status: str = Field(..., description="Overall compliance status (PASS, FAIL)")
    passed_check_count: int = Field(..., description="Number of passed topological checks")
    failed_check_count: int = Field(..., description="Number of failed topological checks")
    checks: List[TopologyCheck] = Field(..., description="Individual rule evaluation results")
    processing_method: str = Field("Rule-Based 3D Cadastral Topology Validation", description="Processing engine label")
    data_classification: str = Field("Prototype Cadastral Data", description="Data integrity status")


class TopologyAllPropertiesResponse(BaseModel):
    processing_method: str = Field("Rule-Based 3D Cadastral Topology Validation", description="Processing engine label")
    total_properties_validated: int = Field(..., description="Total properties evaluated")
    compliant_properties_count: int = Field(..., description="Properties passing 100% of topology rules")
    non_compliant_properties_count: int = Field(..., description="Properties with 1 or more failed topology rules")
    validations: List[TopologyValidationResponse] = Field(..., description="Per-property validation breakdown")
