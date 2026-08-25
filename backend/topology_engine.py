from typing import List, Dict, Optional
from models import (
    TopologyCheck,
    TopologyValidationResponse,
    TopologyAllPropertiesResponse
)
from conflict_engine import (
    CADASTRAL_3D_VOLUMES,
    get_conflicts_for_property
)
from database import PROTOTYPE_PARCELS

BASE_PARCEL_ID = "p9402"

def validate_property_topology(property_id: str) -> Optional[TopologyValidationResponse]:
    """
    Performs comprehensive rule-based 3D cadastral topology validation on a specific registered volume.
    Evaluates:
      1. NON_OVERLAP
      2. FOOTPRINT_CONSISTENCY
      3. VERTICAL_CONTINUITY
      4. SUBTERRANEAN_BUFFER
    """
    target_key = property_id.strip().lower()
    
    # Locate registered volume
    matched_key = None
    for k in CADASTRAL_3D_VOLUMES.keys():
        if k.lower() == target_key:
            matched_key = k
            break
            
    if not matched_key:
        return None

    volume_data = CADASTRAL_3D_VOLUMES[matched_key]
    prop_id = volume_data["property_id"]
    prop_name = volume_data["name"]
    box = volume_data["box"]

    checks: List[TopologyCheck] = []
    
    # -------------------------------------------------------------
    # RULE 1: NON_OVERLAP
    # -------------------------------------------------------------
    conflicts = get_conflicts_for_property(prop_id) or []
    if conflicts:
        primary = conflicts[0]
        checks.append(
            TopologyCheck(
                check_id="TOP-01",
                check_name="NON_OVERLAP",
                status="FAIL",
                description=f"Volumetric conflict detected: {primary.overlap_volume_m3} m³ overlap with {primary.property_b_name}.",
                property_id=prop_id,
                related_property_id=primary.property_b,
                measured_value=f"Overlap Volume = {primary.overlap_volume_m3} m³",
                expected_condition="Overlap Volume == 0.00 m³"
            )
        )
    else:
        checks.append(
            TopologyCheck(
                check_id="TOP-01",
                check_name="NON_OVERLAP",
                status="PASS",
                description="Zero volumetric collisions with adjacent cadastral volumes.",
                property_id=prop_id,
                related_property_id=None,
                measured_value="Overlap Volume = 0.00 m³",
                expected_condition="Overlap Volume == 0.00 m³"
            )
        )

    # -------------------------------------------------------------
    # RULE 2: FOOTPRINT_CONSISTENCY
    # Base Parcel P9402: X in [-8.0, 8.0], Z in [-8.0, 8.0]
    # -------------------------------------------------------------
    parcel = PROTOTYPE_PARCELS.get(BASE_PARCEL_ID)
    p_min_x = parcel.min_x if parcel else -8.0
    p_max_x = parcel.max_x if parcel else 8.0
    p_min_z = parcel.min_z if parcel else -8.0
    p_max_z = parcel.max_z if parcel else 8.0

    is_footprint_inside = (
        box.min_x >= p_min_x and
        box.max_x <= p_max_x and
        box.min_z >= p_min_z and
        box.max_z <= p_max_z
    )

    if is_footprint_inside:
        checks.append(
            TopologyCheck(
                check_id="TOP-02",
                check_name="FOOTPRINT_CONSISTENCY",
                status="PASS",
                description=f"Horizontal footprint [{box.min_x:+.2f}, {box.max_x:+.2f}] × [{box.min_z:+.2f}, {box.max_z:+.2f}] lies strictly inside Base Parcel P9402.",
                property_id=prop_id,
                related_property_id="P9402",
                measured_value=f"X: [{box.min_x:+.2f}, {box.max_x:+.2f}], Z: [{box.min_z:+.2f}, {box.max_z:+.2f}]",
                expected_condition=f"Inside Parcel Bounds X: [{p_min_x:+.2f}, {p_max_x:+.2f}], Z: [{p_min_z:+.2f}, {p_max_z:+.2f}]"
            )
        )
    else:
        # Calculate maximum extension beyond boundary
        ext_x = max(0.0, p_min_x - box.min_x, box.max_x - p_max_x)
        ext_z = max(0.0, p_min_z - box.min_z, box.max_z - p_max_z)
        max_ext = max(ext_x, ext_z)
        
        checks.append(
            TopologyCheck(
                check_id="TOP-02",
                check_name="FOOTPRINT_CONSISTENCY",
                status="FAIL",
                description=f"Horizontal boundary extends {max_ext:.2f}m beyond registered Base Parcel P9402 line.",
                property_id=prop_id,
                related_property_id="P9402",
                measured_value=f"X: [{box.min_x:+.2f}, {box.max_x:+.2f}], Z: [{box.min_z:+.2f}, {box.max_z:+.2f}] (Overhang: {max_ext:.2f}m)",
                expected_condition=f"Inside Parcel Bounds X: [{p_min_x:+.2f}, {p_max_x:+.2f}], Z: [{p_min_z:+.2f}, {p_max_z:+.2f}]"
            )
        )

    # -------------------------------------------------------------
    # RULE 3: VERTICAL_CONTINUITY
    # -------------------------------------------------------------
    vertical_extent = box.max_y - box.min_y
    if box.min_y < box.max_y and vertical_extent > 0:
        checks.append(
            TopologyCheck(
                check_id="TOP-03",
                check_name="VERTICAL_CONTINUITY",
                status="PASS",
                description=f"Valid positive vertical height span: {vertical_extent:.2f}m (Elevation: {box.min_y:+.2f}m to {box.max_y:+.2f}m MSL).",
                property_id=prop_id,
                related_property_id=None,
                measured_value=f"Vertical Extent = {vertical_extent:.2f}m (min_y: {box.min_y:+.2f}, max_y: {box.max_y:+.2f})",
                expected_condition="min_y < max_y and vertical_extent > 0"
            )
        )
    else:
        checks.append(
            TopologyCheck(
                check_id="TOP-03",
                check_name="VERTICAL_CONTINUITY",
                status="FAIL",
                description="Invalid or non-positive vertical elevation interval.",
                property_id=prop_id,
                related_property_id=None,
                measured_value=f"Vertical Extent = {vertical_extent:.2f}m",
                expected_condition="min_y < max_y and vertical_extent > 0"
            )
        )

    # -------------------------------------------------------------
    # RULE 4: SUBTERRANEAN_BUFFER (Prototype Subterranean Buffer Rule)
    # Underground volumes (min_y < 0.0) must maintain >= 0.20m surface clearance (max_y <= -0.20m)
    # and bedrock clearance (min_y >= -15.0m).
    # -------------------------------------------------------------
    is_underground = box.min_y < 0.0
    if is_underground:
        surface_clearance = 0.0 - box.max_y
        bedrock_clearance = box.min_y - (-15.0)
        
        if surface_clearance >= 0.20 and bedrock_clearance >= 0.0:
            checks.append(
                TopologyCheck(
                    check_id="TOP-04",
                    check_name="SUBTERRANEAN_BUFFER",
                    status="PASS",
                    description=f"Subterranean volume maintains {surface_clearance:.2f}m surface buffer and safe bedrock clearance.",
                    property_id=prop_id,
                    related_property_id="GROUND_DATUM_0.0M",
                    measured_value=f"Ground Surface Clearance = {surface_clearance:.2f}m, Foundation Depth = {box.min_y:+.2f}m",
                    expected_condition="Surface Clearance >= 0.20m and min_y >= -15.00m (Prototype Subterranean Buffer Rule)"
                )
            )
        else:
            checks.append(
                TopologyCheck(
                    check_id="TOP-04",
                    check_name="SUBTERRANEAN_BUFFER",
                    status="FAIL",
                    description=f"Subterranean volume violates underground buffer: surface clearance is {surface_clearance:.2f}m (< 0.20m required).",
                    property_id=prop_id,
                    related_property_id="GROUND_DATUM_0.0M",
                    measured_value=f"Ground Surface Clearance = {surface_clearance:.2f}m",
                    expected_condition="Surface Clearance >= 0.20m and min_y >= -15.00m (Prototype Subterranean Buffer Rule)"
                )
            )
    else:
        checks.append(
            TopologyCheck(
                check_id="TOP-04",
                check_name="SUBTERRANEAN_BUFFER",
                status="PASS",
                description="Above-ground volume compliant with ground datum elevation (MSL >= +0.00m).",
                property_id=prop_id,
                related_property_id="GROUND_DATUM_0.0M",
                measured_value=f"Base Elevation = {box.min_y:+.2f}m MSL",
                expected_condition="Above-Ground Elevation (Y >= 0.00m)"
            )
        )

    failed_count = sum(1 for c in checks if c.status == "FAIL")
    passed_count = sum(1 for c in checks if c.status == "PASS")
    overall_status = "PASS" if failed_count == 0 else "FAIL"

    return TopologyValidationResponse(
        validation_id=f"TOPO-VAL-{prop_id.upper()}-01",
        property_id=prop_id,
        property_name=prop_name,
        overall_status=overall_status,
        passed_check_count=passed_count,
        failed_check_count=failed_count,
        checks=checks,
        processing_method="Rule-Based 3D Cadastral Topology Validation",
        data_classification="Prototype Cadastral Data"
    )


def validate_all_properties_topology() -> TopologyAllPropertiesResponse:
    """
    Validates all registered 3D property volumes against the 4 topological rules.
    """
    results: List[TopologyValidationResponse] = []
    
    for key in CADASTRAL_3D_VOLUMES.keys():
        val = validate_property_topology(key)
        if val:
            results.append(val)

    compliant = sum(1 for r in results if r.overall_status == "PASS")
    non_compliant = sum(1 for r in results if r.overall_status == "FAIL")

    return TopologyAllPropertiesResponse(
        processing_method="Rule-Based 3D Cadastral Topology Validation",
        total_properties_validated=len(results),
        compliant_properties_count=compliant,
        non_compliant_properties_count=non_compliant,
        validations=results
    )
