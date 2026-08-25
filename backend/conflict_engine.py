from typing import List, Dict, Tuple, Optional
from models import (
    BoundingBox3D,
    OverlapBounds,
    ConflictResult,
    ConflictPairSummary,
    ConflictMatrixResponse,
    ConflictListResponse
)

# Structure defining registered 3D cadastral volumes derived from project geometry
CADASTRAL_3D_VOLUMES: Dict[str, Dict] = {
    "U401": {
        "property_id": "U401",
        "name": "Balcony Cantilever Extension (Unit 401)",
        "ulpin": "IN-KA-560001-P9402-Z+015.5-U401",
        "box": BoundingBox3D(
            min_x=-11.05, max_x=-6.55,
            min_y=13.95, max_y=16.45,
            min_z=-5.55, max_z=-2.05
        )
    },
    "U402": {
        "property_id": "U402",
        "name": "Unit 402 (Floor 4 Wing B)",
        "ulpin": "IN-KA-560001-P9402-Z+015.5-U402",
        "box": BoundingBox3D(
            min_x=0.20, max_x=7.40,
            min_y=13.80, max_y=16.80,
            min_z=-7.40, max_z=-0.20
        )
    },
    "ground-commercial": {
        "property_id": "ground-commercial",
        "name": "Commercial Suite G-01 (Ground Floor Retail)",
        "ulpin": "IN-KA-560001-P9402-Z+000.1-COMM",
        "box": BoundingBox3D(
            min_x=-8.00, max_x=8.00,
            min_y=0.10, max_y=3.90,
            min_z=-8.00, max_z=8.00
        )
    },
    "b1": {
        "property_id": "b1",
        "name": "Subterranean Level B1 - Automated Parking",
        "ulpin": "IN-KA-560001-P9402-Z-004.8-SUB1",
        "box": BoundingBox3D(
            min_x=-9.00, max_x=9.00,
            min_y=-4.80, max_y=-0.30,
            min_z=-9.00, max_z=9.00
        )
    },
    "air-rights": {
        "property_id": "air-rights",
        "name": "Rooftop Air Rights & TDR Envelope",
        "ulpin": "IN-KA-560001-P9402-Z+025.5-AIR",
        "box": BoundingBox3D(
            min_x=-8.00, max_x=8.00,
            min_y=25.50, max_y=43.50,
            min_z=-8.00, max_z=8.00
        )
    },
    "municipal-setback": {
        "property_id": "municipal-setback",
        "name": "Municipal Right-of-Way Airspace Parcel",
        "ulpin": "IN-KA-560001-ROW-SETBACK-01",
        "box": BoundingBox3D(
            min_x=-18.00, max_x=-10.00,
            min_y=0.00, max_y=30.00,
            min_z=-10.00, max_z=10.00
        )
    }
}


def compute_3d_aabb_intersection(boxA: BoundingBox3D, boxB: BoundingBox3D) -> Tuple[bool, float, Optional[OverlapBounds]]:
    """
    Performs dynamic 3D Axis-Aligned Bounding Box (AABB) intersection calculation.
    
    Formula:
      overlap_min_x = max(boxA.min_x, boxB.min_x)
      overlap_max_x = min(boxA.max_x, boxB.max_x)
      overlap_min_y = max(boxA.min_y, boxB.min_y)
      overlap_max_y = min(boxA.max_y, boxB.max_y)
      overlap_min_z = max(boxA.min_z, boxB.min_z)
      overlap_max_z = min(boxA.max_z, boxB.max_z)
    """
    overlap_min_x = max(boxA.min_x, boxB.min_x)
    overlap_max_x = min(boxA.max_x, boxB.max_x)
    overlap_min_y = max(boxA.min_y, boxB.min_y)
    overlap_max_y = min(boxA.max_y, boxB.max_y)
    overlap_min_z = max(boxA.min_z, boxB.min_z)
    overlap_max_z = min(boxA.max_z, boxB.max_z)

    # Check for non-overlap along any 1D dimension
    if (overlap_min_x >= overlap_max_x) or (overlap_min_y >= overlap_max_y) or (overlap_min_z >= overlap_max_z):
        return False, 0.0, None

    width = overlap_max_x - overlap_min_x
    height = overlap_max_y - overlap_min_y
    depth = overlap_max_z - overlap_min_z
    volume = width * height * depth

    if volume <= 0.001:
        return False, 0.0, None

    bounds = OverlapBounds(
        min_x=round(overlap_min_x, 3),
        max_x=round(overlap_max_x, 3),
        min_y=round(overlap_min_y, 3),
        max_y=round(overlap_max_y, 3),
        min_z=round(overlap_min_z, 3),
        max_z=round(overlap_max_z, 3),
        width_m=round(width, 3),
        height_m=round(height, 3),
        depth_m=round(depth, 3)
    )

    return True, round(volume, 2), bounds


def evaluate_all_conflicts() -> List[ConflictResult]:
    """
    Evaluates all unique unordered pairs among registered 3D cadastral volumes
    and returns detected volumetric overlap conflicts.
    """
    keys = list(CADASTRAL_3D_VOLUMES.keys())
    conflicts: List[ConflictResult] = []
    
    conflict_counter = 1

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            key_a = keys[i]
            key_b = keys[j]

            vol_a = CADASTRAL_3D_VOLUMES[key_a]
            vol_b = CADASTRAL_3D_VOLUMES[key_b]

            is_overlap, vol, bounds = compute_3d_aabb_intersection(vol_a["box"], vol_b["box"])

            if is_overlap:
                conflict_id = f"CONF-{vol_a['property_id'].upper()}-{vol_b['property_id'].upper()}-{conflict_counter:02d}"
                conflicts.append(
                    ConflictResult(
                        conflict_id=conflict_id,
                        property_a=vol_a["property_id"],
                        property_b=vol_b["property_id"],
                        property_a_name=vol_a["name"],
                        property_b_name=vol_b["name"],
                        overlap_exists=True,
                        overlap_volume_m3=vol,
                        overlap_bounds=bounds,
                        conflict_type="3D Boundary / Volumetric Overlap",
                        severity="HIGH",
                        status="DISPUTED",
                        processing_method="Rule-Based 3D AABB Intersection",
                        data_classification="Prototype Cadastral Data"
                    )
                )
                conflict_counter += 1

    return conflicts


def get_conflicts_for_property(property_id: str) -> Optional[List[ConflictResult]]:
    """
    Returns all conflicts involving the specified property identifier.
    Returns None if the property is not registered in the 3D volume database.
    """
    target_key = property_id.strip().lower()
    
    # Check if property exists
    matched_key = None
    for k in CADASTRAL_3D_VOLUMES.keys():
        if k.lower() == target_key:
            matched_key = k
            break
            
    if not matched_key:
        return None

    all_conflicts = evaluate_all_conflicts()
    return [
        c for c in all_conflicts
        if c.property_a.lower() == target_key or c.property_b.lower() == target_key
    ]


def get_conflict_by_id(conflict_id: str) -> Optional[ConflictResult]:
    """
    Retrieves a single conflict record by its unique conflict_id.
    """
    target_id = conflict_id.strip().upper()
    all_conflicts = evaluate_all_conflicts()
    for c in all_conflicts:
        if c.conflict_id.upper() == target_id:
            return c
    return None


def get_conflict_matrix() -> ConflictMatrixResponse:
    """
    Computes a complete, non-duplicate pairwise conflict matrix across all registered 3D volumes.
    """
    keys = list(CADASTRAL_3D_VOLUMES.keys())
    matrix: List[ConflictPairSummary] = []
    
    total_disputed_vol = 0.0
    conflicts_count = 0

    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            key_a = keys[i]
            key_b = keys[j]

            vol_a = CADASTRAL_3D_VOLUMES[key_a]
            vol_b = CADASTRAL_3D_VOLUMES[key_b]

            is_overlap, vol, _ = compute_3d_aabb_intersection(vol_a["box"], vol_b["box"])

            if is_overlap:
                conflicts_count += 1
                total_disputed_vol += vol
                status = "DISPUTED"
            else:
                status = "NO_CONFLICT"

            matrix.append(
                ConflictPairSummary(
                    property_a=vol_a["property_id"],
                    property_b=vol_b["property_id"],
                    overlap_exists=is_overlap,
                    overlap_volume_m3=vol,
                    status=status
                )
            )

    return ConflictMatrixResponse(
        processing_method="Rule-Based 3D AABB Intersection",
        evaluated_properties=keys,
        total_pairs_evaluated=len(matrix),
        conflicts_detected_count=conflicts_count,
        total_disputed_volume_m3=round(total_disputed_vol, 2),
        matrix=matrix
    )
