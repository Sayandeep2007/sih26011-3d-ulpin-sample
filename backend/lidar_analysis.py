import random
from typing import List, Dict, Tuple, Any
from models import (
    LiDARPoint,
    LiDARStratum,
    LiDARStrataResponse,
    LiDARAnalysisResponse,
    LiDARMetadataResponse,
    LiDARSampleResponse
)

# Deterministic prototype LiDAR Point Cloud Generation (6,000 points matching frontend dataset)
def generate_deterministic_lidar_points(count: int = 6000, seed: int = 42) -> List[Tuple[float, float, float]]:
    """
    Generates a deterministic 6,000-point LiDAR survey dataset matching the spatial distribution
    and elevation boundaries of the GeoCadastre-3D prototype.
    """
    rng = random.Random(seed)
    points: List[Tuple[float, float, float]] = []
    
    for _ in range(count):
        ux = (rng.random() - 0.5) * 19.0
        uy = rng.random() * 32.0 - 10.0
        uz = (rng.random() - 0.5) * 19.0
        points.append((ux, uy, uz))
        
    return points

# In-memory singleton dataset
PROTOTYPE_LIDAR_POINTS: List[Tuple[float, float, float]] = generate_deterministic_lidar_points(6000, seed=42)

def analyze_lidar_points(points: List[Tuple[float, float, float]]) -> LiDARAnalysisResponse:
    """
    Performs live mathematical and spatial analysis on the provided LiDAR point array.
    Calculates spatial bounds, extents, enclosure volumes, and vertical strata dynamically.
    """
    if not points:
        raise ValueError("Cannot analyze empty point cloud dataset")

    total_points = len(points)
    
    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    min_z = min(p[2] for p in points)
    max_z = max(p[2] for p in points)

    span_x = max_x - min_x
    vertical_span = max_y - min_y
    span_z = max_z - min_z
    
    enclosure_volume = span_x * vertical_span * span_z
    bounding_extent = f"{span_x:.2f}m (W) × {vertical_span:.2f}m (H) × {span_z:.2f}m (D)"

    # Vertical Stratification Rules (Matching frontend prototype)
    strata_definitions = [
        ("Subterranean", lambda y: y < 0.0, -10.0, 0.0),
        ("Ground / Commercial", lambda y: 0.0 <= y < 4.0, 0.0, 4.0),
        ("Floor 1", lambda y: 4.2 <= y <= 7.2, 4.2, 7.2),
        ("Floor 2", lambda y: 7.4 <= y <= 10.4, 7.4, 10.4),
        ("Floor 3", lambda y: 10.6 <= y <= 13.6, 10.6, 13.6),
        ("Floor 4", lambda y: 13.8 <= y <= 16.8, 13.8, 16.8),
        ("Floor 5", lambda y: 17.0 <= y <= 20.0, 17.0, 20.0),
        ("Rooftop / Air Rights", lambda y: y >= 20.0, 20.0, 22.0),
    ]

    calculated_strata: List[LiDARStratum] = []
    for name, condition, def_min_y, def_max_y in strata_definitions:
        matched_pts = [p for p in points if condition(p[1])]
        cnt = len(matched_pts)
        pct = round((cnt / total_points) * 100, 2)
        
        actual_min_y = round(min(p[1] for p in matched_pts), 2) if matched_pts else def_min_y
        actual_max_y = round(max(p[1] for p in matched_pts), 2) if matched_pts else def_max_y

        calculated_strata.append(
            LiDARStratum(
                name=name,
                elevation_min_m=actual_min_y,
                elevation_max_m=actual_max_y,
                point_count=cnt,
                percentage=pct,
                processing_method="Rule-Based Geometric Vertical Segmentation"
            )
        )

    return LiDARAnalysisResponse(
        project="GeoCadastre-3D",
        survey_classification="Prototype Survey TLS",
        coordinate_reference="Local Cadastral Ground Origin (MSL Datum +0.00m) - LOCAL_XYZ",
        total_points=total_points,
        min_x=round(min_x, 2),
        max_x=round(max_x, 2),
        min_y=round(min_y, 2),
        max_y=round(max_y, 2),
        min_z=round(min_z, 2),
        max_z=round(max_z, 2),
        span_x=round(span_x, 2),
        vertical_span=round(vertical_span, 2),
        span_z=round(span_z, 2),
        bounding_extent=bounding_extent,
        enclosure_volume_m3=round(enclosure_volume, 2),
        processing_method="Rule-Based Geometric Analysis",
        data_integrity_note="Prototype survey point cloud. Calculated dynamically from 6,000 spatial survey points.",
        strata=calculated_strata
    )

def get_lidar_strata() -> LiDARStrataResponse:
    analysis = analyze_lidar_points(PROTOTYPE_LIDAR_POINTS)
    return LiDARStrataResponse(
        project=analysis.project,
        survey_classification=analysis.survey_classification,
        total_points=analysis.total_points,
        processing_method="Rule-Based Geometric Vertical Segmentation",
        strata=analysis.strata
    )

def get_lidar_sample(limit: int = 10) -> LiDARSampleResponse:
    sample_points = [
        LiDARPoint(id=i + 1, x=round(p[0], 3), y=round(p[1], 3), z=round(p[2], 3))
        for i, p in enumerate(PROTOTYPE_LIDAR_POINTS[:limit])
    ]
    return LiDARSampleResponse(
        sample_type="Diagnostic sample — not complete point cloud",
        sample_size=len(sample_points),
        total_point_cloud_size=len(PROTOTYPE_LIDAR_POINTS),
        points=sample_points
    )

def generate_lidar_text_report() -> str:
    analysis = analyze_lidar_points(PROTOTYPE_LIDAR_POINTS)
    
    report_lines = [
        "================================================================================",
        "                         LIDAR SURVEY ANALYSIS REPORT                          ",
        "                            GEOCADASTRE-3D BACKEND                             ",
        "================================================================================",
        "",
        "PROJECT INFORMATION:",
        f"  Project Name          : {analysis.project}",
        f"  Survey Classification : {analysis.survey_classification}",
        f"  Coordinate Reference  : {analysis.coordinate_reference}",
        f"  Processing Engine     : {analysis.processing_method}",
        "",
        "POINT CLOUD METRIC ANALYSIS:",
        f"  Total Survey Points   : {analysis.total_points:,} pts",
        f"  Elevation Minimum     : {analysis.min_y:+.2f} m MSL",
        f"  Elevation Maximum     : {analysis.max_y:+.2f} m MSL",
        f"  Vertical Span         : {analysis.vertical_span:.2f} m",
        f"  Horizontal Span (X)   : {analysis.min_x:+.2f}m to {analysis.max_x:+.2f}m (Span: {analysis.span_x:.2f} m)",
        f"  Horizontal Span (Z)   : {analysis.min_z:+.2f}m to {analysis.max_z:+.2f}m (Span: {analysis.span_z:.2f} m)",
        f"  3D Bounding Extent    : {analysis.bounding_extent}",
        f"  Enclosure Volume      : {analysis.enclosure_volume_m3:,.2f} cu m",
        "",
        "VERTICAL STRATIFICATION (RULE-BASED GEOMETRIC SEGMENTATION):",
        "--------------------------------------------------------------------------------",
        "  Stratum Name         | Elevation Range          | Points   | Share (%) ",
        "--------------------------------------------------------------------------------"
    ]

    for s in analysis.strata:
        report_lines.append(
            f"  {s.name:<20} | {s.elevation_min_m:>+6.2f}m to {s.elevation_max_m:>+6.2f}m MSL | {s.point_count:>6} pts | {s.percentage:>6.2f} %"
        )

    report_lines.extend([
        "--------------------------------------------------------------------------------",
        "",
        "CADASTRAL INTEGRATION & DATA INTEGRITY:",
        "  - The survey point cloud is dynamically linked to 2D Parcel P9402 and 3D ULPIN models.",
        "  - Prototype geometric segmentation. AI/ML semantic extraction is a future processing stage.",
        "  - Inter-floor slab intervals (0.2m) unassigned, maintaining structural fidelity.",
        "",
        "================================================================================",
        "END OF REPORT"
    ])

    return "\n".join(report_lines)
