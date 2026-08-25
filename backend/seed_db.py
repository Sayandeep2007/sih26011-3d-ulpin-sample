"""
GeoCadastre-3D Development Database Seeding Script (Day 6 Step 1B)
Idempotent insertion of baseline prototype cadastral, LiDAR, conflict, and topology records.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from db_models import (
    ParcelModel, PropertyModel, LidarSurveyModel,
    ConflictModel, TopologyValidationModel, TopologyCheckModel
)
from database import PROTOTYPE_PROPERTIES, PROTOTYPE_PARCELS
from models import LiDARMetadataResponse
from lidar_analysis import analyze_lidar_points, PROTOTYPE_LIDAR_POINTS
from conflict_engine import evaluate_all_conflicts
from topology_engine import validate_all_properties_topology


def seed_database() -> dict:
    """
    Idempotently seeds baseline development cadastral data.
    Checks for record existence by primary key before insertion.
    Running multiple times produces zero duplicates.
    """
    session = SessionLocal()
    stats = {
        "parcels_inserted": 0, "parcels_skipped": 0,
        "properties_inserted": 0, "properties_skipped": 0,
        "surveys_inserted": 0, "surveys_skipped": 0,
        "conflicts_inserted": 0, "conflicts_skipped": 0,
        "topology_validations_inserted": 0, "topology_validations_skipped": 0,
        "topology_checks_inserted": 0, "topology_checks_skipped": 0,
    }

    try:
        # 1. Seed Base Cadastral Parcels
        for key, p_data in PROTOTYPE_PARCELS.items():
            existing = session.get(ParcelModel, p_data.parcel_id)
            if not existing:
                parcel = ParcelModel(
                    parcel_id=p_data.parcel_id,
                    survey_number=p_data.survey_number,
                    location_name=p_data.location_name,
                    ulpin_base=p_data.ulpin_base,
                    coordinate_reference=p_data.coordinate_reference,
                    min_x=p_data.min_x,
                    max_x=p_data.max_x,
                    min_z=p_data.min_z,
                    max_z=p_data.max_z,
                    width_m=p_data.width_m,
                    depth_m=p_data.depth_m,
                    area_m2=p_data.area_m2,
                    elevation_min_m=p_data.elevation_min_m,
                    elevation_max_m=p_data.elevation_max_m,
                    status=p_data.status,
                    data_classification=p_data.data_classification,
                    gnss_cors_note=p_data.gnss_cors_note or "GNSS/CORS integration point: prototype"
                )
                session.add(parcel)
                stats["parcels_inserted"] += 1
            else:
                stats["parcels_skipped"] += 1

        session.commit()

        # 2. Seed 3D Cadastral Properties / Volumetric Units
        for key, prop_data in PROTOTYPE_PROPERTIES.items():
            existing = session.get(PropertyModel, prop_data.property_id)
            if not existing:
                prop = PropertyModel(
                    property_id=prop_data.property_id,
                    unit=prop_data.unit,
                    property_type=prop_data.property_type,
                    floor=prop_data.floor,
                    ulpin=prop_data.ulpin,
                    parcel_id="P9402",  # Standard base parcel
                    elevation_min_m=prop_data.elevation_min_m,
                    elevation_max_m=prop_data.elevation_max_m,
                    status=prop_data.status,
                    owner=prop_data.owner,
                    classification=prop_data.classification,
                    has_conflict=prop_data.has_conflict,
                    conflict_desc=prop_data.conflict_desc
                )
                session.add(prop)
                stats["properties_inserted"] += 1
            else:
                stats["properties_skipped"] += 1

        session.commit()

        # 3. Seed LiDAR Survey Metadata Record
        lidar_analysis = analyze_lidar_points(PROTOTYPE_LIDAR_POINTS)
        lidar_meta = LiDARMetadataResponse()
        existing_survey = session.get(LidarSurveyModel, "LS-BLR-2026-001")
        if not existing_survey and lidar_analysis:
            survey = LidarSurveyModel(
                survey_id="LS-BLR-2026-001",
                parcel_id="P9402",
                data_source_type=lidar_meta.data_source_type,
                sensor_model="Trimble TX8 / Leica ScanStation P40 (Simulated)",
                total_points=lidar_analysis.total_points,
                min_x=lidar_analysis.min_x,
                max_x=lidar_analysis.max_x,
                min_y=lidar_analysis.min_y,
                max_y=lidar_analysis.max_y,
                min_z=lidar_analysis.min_z,
                max_z=lidar_analysis.max_z,
                span_x=lidar_analysis.span_x,
                vertical_span=lidar_analysis.vertical_span,
                span_z=lidar_analysis.span_z,
                enclosure_volume_m3=lidar_analysis.enclosure_volume_m3,
                bounding_extent=lidar_analysis.bounding_extent,
                data_classification=lidar_meta.survey_classification,
                notes="Baseline prototype terrestrial laser scan survey (6,000 points)."
            )
            session.add(survey)
            stats["surveys_inserted"] += 1
        else:
            stats["surveys_skipped"] += 1

        session.commit()

        # 4. Seed 3D Spatial Conflicts
        conflicts_list = evaluate_all_conflicts()
        for c in conflicts_list:
            existing_c = session.get(ConflictModel, c.conflict_id)
            if not existing_c:
                ob = c.overlap_bounds
                conf_record = ConflictModel(
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
                    overlap_min_x=ob.min_x if ob else 0.0,
                    overlap_max_x=ob.max_x if ob else 0.0,
                    overlap_min_y=ob.min_y if ob else 0.0,
                    overlap_max_y=ob.max_y if ob else 0.0,
                    overlap_min_z=ob.min_z if ob else 0.0,
                    overlap_max_z=ob.max_z if ob else 0.0,
                    overlap_width_m=ob.width_m if ob else 0.0,
                    overlap_height_m=ob.height_m if ob else 0.0,
                    overlap_depth_m=ob.depth_m if ob else 0.0,
                    processing_method=c.processing_method,
                    data_classification=c.data_classification
                )
                session.add(conf_record)
                stats["conflicts_inserted"] += 1
            else:
                stats["conflicts_skipped"] += 1

        session.commit()

        # 5. Seed 3D Cadastral Topology Validations & Checks
        all_topo = validate_all_properties_topology()
        for val_resp in all_topo.validations:
            existing_v = session.get(TopologyValidationModel, val_resp.validation_id)
            if not existing_v:
                topo_val = TopologyValidationModel(
                    validation_id=val_resp.validation_id,
                    property_id=val_resp.property_id,
                    property_name=val_resp.property_name,
                    overall_status=val_resp.overall_status,
                    passed_check_count=val_resp.passed_check_count,
                    failed_check_count=val_resp.failed_check_count,
                    processing_method=val_resp.processing_method,
                    data_classification=val_resp.data_classification
                )
                session.add(topo_val)
                session.flush()
                stats["topology_validations_inserted"] += 1

                for chk in val_resp.checks:
                    chk_record = TopologyCheckModel(
                        validation_id=val_resp.validation_id,
                        check_id=chk.check_id,
                        check_name=chk.check_name,
                        status=chk.status,
                        description=chk.description,
                        property_id=chk.property_id,
                        related_property_id=chk.related_property_id,
                        measured_value=chk.measured_value,
                        expected_condition=chk.expected_condition,
                        processing_method=chk.processing_method,
                        data_classification=chk.data_classification
                    )
                    session.add(chk_record)
                    stats["topology_checks_inserted"] += 1
            else:
                stats["topology_validations_skipped"] += 1
                stats["topology_checks_skipped"] += len(val_resp.checks)

        session.commit()

    except Exception as e:
        session.rollback()
        print(f"ERROR: Seeding failed with exception: {e}")
        raise
    finally:
        session.close()

    return stats


if __name__ == "__main__":
    print("=" * 60)
    print("GeoCadastre-3D Database Seeder")
    print("=" * 60)
    res = seed_database()
    print("Seed Summary:")
    for k, v in res.items():
        print(f"  - {k:<32}: {v}")
    print("=" * 60)
