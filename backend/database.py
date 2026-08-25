from typing import Dict, List, Optional, Any
from models import PropertyResponse, ParcelResponse, GeoJsonFeature, ParcelSummaryResponse

PROTOTYPE_PROPERTIES: Dict[str, PropertyResponse] = {
    "u401": PropertyResponse(
        property_id="U401",
        unit="Unit 401 (Balcony Cantilever Extension)",
        property_type="Residential Apartment",
        floor=4,
        ulpin="IN-KA-560001-P9402-Z+015.5-U401",
        parcel_id="IN-KA-560001-P9402",
        elevation_min_m=13.8,
        elevation_max_m=16.8,
        status="DISPUTED",
        owner="Prototype Owner (Sample Data)",
        classification="Prototype Cadastral Record",
        has_conflict=True,
        conflict_desc="Balcony cantilever volume illegally extends 1.85m beyond cadastral setback into Municipal Right-of-Way air envelope."
    ),
    "u402": PropertyResponse(
        property_id="U402",
        unit="Unit 402 (4th Floor Wing B)",
        property_type="Residential Apartment",
        floor=4,
        ulpin="IN-KA-560001-P9402-Z+015.5-U402",
        parcel_id="IN-KA-560001-P9402",
        elevation_min_m=13.8,
        elevation_max_m=16.8,
        status="REGISTERED",
        owner="Prototype Owner (Sample Data)",
        classification="Prototype Cadastral Record",
        has_conflict=False,
        conflict_desc=None
    ),
    "ground-commercial": PropertyResponse(
        property_id="ground-commercial",
        unit="Ground Commercial Retail & Atrium",
        property_type="Commercial",
        floor=0,
        ulpin="IN-KA-560001-P9402-Z+000.1-COMM",
        parcel_id="IN-KA-560001-P9402",
        elevation_min_m=0.1,
        elevation_max_m=3.9,
        status="REGISTERED",
        owner="Prototype Owner (Sample Data)",
        classification="Prototype Cadastral Record",
        has_conflict=False,
        conflict_desc=None
    ),
    "b1": PropertyResponse(
        property_id="b1",
        unit="Subterranean Level B1 Automated Parking",
        property_type="Subterranean Parking",
        floor=-1,
        ulpin="IN-KA-560001-P9402-Z-004.8-SUB1",
        parcel_id="IN-KA-560001-P9402",
        elevation_min_m=-4.8,
        elevation_max_m=-0.3,
        status="REGISTERED",
        owner="Prototype Owner (Sample Data)",
        classification="Prototype Cadastral Record",
        has_conflict=False,
        conflict_desc=None
    ),
    "air-rights": PropertyResponse(
        property_id="air-rights",
        unit="Rooftop Air Rights & TDR Envelope",
        property_type="Air Rights / TDR Envelope",
        floor=7,
        ulpin="IN-KA-560001-P9402-Z+025.5-AIR",
        parcel_id="IN-KA-560001-P9402",
        elevation_min_m=25.5,
        elevation_max_m=43.5,
        status="REGISTERED",
        owner="Prototype Owner (Sample Data)",
        classification="Prototype Cadastral Record",
        has_conflict=False,
        conflict_desc=None
    ),
}

PROTOTYPE_PARCELS: Dict[str, ParcelResponse] = {
    "p9402": ParcelResponse(
        parcel_id="P9402",
        survey_number="42/1",
        location_name="Cubbon Road, Ward 110 (Sampangirama Nagar), Bengaluru",
        ulpin_base="IN-KA-560001-P9402",
        coordinate_reference="Local Cadastral Ground Origin (MSL Datum +0.00m) - LOCAL_XZ_CADASTRAL",
        min_x=-8.0,
        max_x=8.0,
        min_z=-8.0,
        max_z=8.0,
        width_m=16.0,
        depth_m=16.0,
        area_m2=256.0,
        elevation_min_m=-12.0,
        elevation_max_m=45.0,
        status="REGISTERED",
        data_classification="Prototype Cadastral Data",
        gnss_cors_note="GNSS/CORS integration point: prototype"
    )
}

# --- Property Access Functions ---

def get_all_properties() -> List[PropertyResponse]:
    return list(PROTOTYPE_PROPERTIES.values())

def get_property_by_id(prop_id: str) -> Optional[PropertyResponse]:
    normalized_key = prop_id.strip().lower()
    return PROTOTYPE_PROPERTIES.get(normalized_key)

def get_property_by_ulpin(ulpin: str) -> Optional[PropertyResponse]:
    target_ulpin = ulpin.strip().upper()
    for prop in PROTOTYPE_PROPERTIES.values():
        if prop.ulpin.upper() == target_ulpin:
            return prop
    return None

# --- Parcel Access Functions ---

def get_all_parcels() -> List[ParcelResponse]:
    return list(PROTOTYPE_PARCELS.values())

def get_parcel_by_id(parcel_id: str) -> Optional[ParcelResponse]:
    normalized_key = parcel_id.strip().lower()
    return PROTOTYPE_PARCELS.get(normalized_key)

def get_properties_for_parcel(parcel_id: str) -> Optional[List[PropertyResponse]]:
    parcel = get_parcel_by_id(parcel_id)
    if not parcel:
        return None
    
    # Filter properties matching this base parcel
    target_pin = parcel.ulpin_base.upper()
    return [p for p in PROTOTYPE_PROPERTIES.values() if p.parcel_id.upper() == target_pin or parcel.parcel_id in p.ulpin]

def get_parcel_geometry(parcel_id: str) -> Optional[GeoJsonFeature]:
    parcel = get_parcel_by_id(parcel_id)
    if not parcel:
        return None

    # Local X/Z Cadastral Boundary Polygon coordinates
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

def get_parcel_summary(parcel_id: str) -> Optional[ParcelSummaryResponse]:
    parcel = get_parcel_by_id(parcel_id)
    if not parcel:
        return None

    associated_props = get_properties_for_parcel(parcel_id) or []
    prop_ids = [p.property_id for p in associated_props]

    return ParcelSummaryResponse(
        parcel_id=parcel.parcel_id,
        survey_number=parcel.survey_number,
        base_ulpin=parcel.ulpin_base,
        area_m2=parcel.area_m2,
        footprint=f"[{parcel.min_x:.1f}, {parcel.max_x:.1f}]m × [{parcel.min_z:.1f}, {parcel.max_z:.1f}]m (Width: {parcel.width_m:.1f}m, Depth: {parcel.depth_m:.1f}m)",
        elevation_range=f"{parcel.elevation_min_m:+.1f}m to {parcel.elevation_max_m:+.1f}m MSL",
        associated_property_count=len(associated_props),
        associated_property_ids=prop_ids,
        data_classification=parcel.data_classification
    )
