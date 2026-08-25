"""
SQLAlchemy 2.x Database ORM Models for GeoCadastre-3D (Day 6 Step 1B)
Provides relational schema definitions for parcels, properties, LiDAR survey metadata,
3D spatial conflicts, and cadastral topology validation results.
"""

from typing import List, Optional
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base


# =========================================================================
# 1. PARCEL ORM MODEL
# =========================================================================

class ParcelModel(Base):
    """
    Represents a registered 2D/3D base land parcel.
    Corresponds to standard cadastral land registry parcels.
    """
    __tablename__ = "parcels"

    parcel_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    survey_number: Mapped[str] = mapped_column(String(64), nullable=False)
    location_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ulpin_base: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    coordinate_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # 2D Bounding Footprint (Local Cartesian X/Z in meters)
    min_x: Mapped[float] = mapped_column(Float, nullable=False)
    max_x: Mapped[float] = mapped_column(Float, nullable=False)
    min_z: Mapped[float] = mapped_column(Float, nullable=False)
    max_z: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Spatial Metrics
    width_m: Mapped[float] = mapped_column(Float, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_min_m: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_max_m: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Administrative Metadata
    status: Mapped[str] = mapped_column(String(64), default="REGISTERED", nullable=False)
    data_classification: Mapped[str] = mapped_column(String(128), default="Prototype Cadastral Data", nullable=False)
    gnss_cors_note: Mapped[str] = mapped_column(String(255), default="GNSS/CORS integration point: prototype")

    # Relationships
    properties: Mapped[List["PropertyModel"]] = relationship(
        "PropertyModel", back_populates="parcel", cascade="all, delete-orphan"
    )


# =========================================================================
# 2. PROPERTY / VOLUMETRIC UNIT ORM MODEL
# =========================================================================

class PropertyModel(Base):
    """
    Represents an individual 3D property unit (e.g. apartment, commercial space,
    subterranean parking, or rooftop air rights volume).
    """
    __tablename__ = "properties"

    property_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    unit: Mapped[str] = mapped_column(String(255), nullable=False)
    property_type: Mapped[str] = mapped_column(String(128), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    ulpin: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    
    # Foreign Key to Parent Parcel
    parcel_id: Mapped[str] = mapped_column(String(64), ForeignKey("parcels.parcel_id"), nullable=False, index=True)
    
    # Vertical Elevation Bounds (MSL Datum in meters)
    elevation_min_m: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_max_m: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Legal & Administrative Status
    status: Mapped[str] = mapped_column(String(64), default="REGISTERED", nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="Prototype Owner (Sample Data)", nullable=False)
    classification: Mapped[str] = mapped_column(String(128), default="Prototype Cadastral Record", nullable=False)
    
    # Conflict Flags
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conflict_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    parcel: Mapped["ParcelModel"] = relationship("ParcelModel", back_populates="properties")


# =========================================================================
# 3. LIDAR SURVEY METADATA ORM MODEL
# =========================================================================

class LidarSurveyModel(Base):
    """
    Stores point cloud survey header metadata and aggregated bounding volume metrics.
    Raw point buffers (e.g. 6,000 points) remain in spatial point files / cache.
    """
    __tablename__ = "lidar_surveys"

    survey_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    parcel_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("parcels.parcel_id"), nullable=True)
    data_source_type: Mapped[str] = mapped_column(String(128), nullable=False)
    sensor_model: Mapped[str] = mapped_column(String(128), nullable=False)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 3D Point Cloud Bounding Extents
    min_x: Mapped[float] = mapped_column(Float, nullable=False)
    max_x: Mapped[float] = mapped_column(Float, nullable=False)
    min_y: Mapped[float] = mapped_column(Float, nullable=False)
    max_y: Mapped[float] = mapped_column(Float, nullable=False)
    min_z: Mapped[float] = mapped_column(Float, nullable=False)
    max_z: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Spans & Volume
    span_x: Mapped[float] = mapped_column(Float, nullable=False)
    vertical_span: Mapped[float] = mapped_column(Float, nullable=False)
    span_z: Mapped[float] = mapped_column(Float, nullable=False)
    enclosure_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    bounding_extent: Mapped[str] = mapped_column(String(128), nullable=False)
    
    data_classification: Mapped[str] = mapped_column(String(128), default="Prototype Survey TLS", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# =========================================================================
# 4. 3D SPATIAL CONFLICT ORM MODEL
# =========================================================================

class ConflictModel(Base):
    """
    Stores detected 3D spatial overlaps, volumetric encumbrances, and boundary disputes.
    """
    __tablename__ = "conflicts"

    conflict_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    property_a: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    property_a_name: Mapped[str] = mapped_column(String(255), nullable=False)
    property_b: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    property_b_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    overlap_exists: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    overlap_volume_m3: Mapped[float] = mapped_column(Float, nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="DISPUTED", nullable=False)
    
    # Overlap Bounding Box (AABB Intersection Prism)
    overlap_min_x: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_max_x: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_min_y: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_max_y: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_min_z: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_max_z: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Dimensions
    overlap_width_m: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_height_m: Mapped[float] = mapped_column(Float, nullable=False)
    overlap_depth_m: Mapped[float] = mapped_column(Float, nullable=False)
    
    processing_method: Mapped[str] = mapped_column(String(128), default="Rule-Based 3D AABB Intersection", nullable=False)
    data_classification: Mapped[str] = mapped_column(String(128), default="Prototype Cadastral Data", nullable=False)


# =========================================================================
# 5. 3D CADASTRAL TOPOLOGY VALIDATION ORM MODEL
# =========================================================================

class TopologyValidationModel(Base):
    """
    Stores 3D cadastral topology validation audit summaries per property.
    """
    __tablename__ = "topology_validations"

    validation_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    property_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    property_name: Mapped[str] = mapped_column(String(255), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(32), nullable=False)
    passed_check_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_check_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    processing_method: Mapped[str] = mapped_column(String(128), default="Rule-Based 3D Cadastral Topology Validation", nullable=False)
    data_classification: Mapped[str] = mapped_column(String(128), default="Prototype Cadastral Data", nullable=False)

    # Relationships
    checks: Mapped[List["TopologyCheckModel"]] = relationship(
        "TopologyCheckModel", back_populates="validation", cascade="all, delete-orphan"
    )


# =========================================================================
# 6. TOPOLOGY INDIVIDUAL CHECK ORM MODEL
# =========================================================================

class TopologyCheckModel(Base):
    """
    Stores individual topology rule evaluations (e.g. TOP-01, TOP-02, TOP-03, TOP-04).
    """
    __tablename__ = "topology_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[str] = mapped_column(String(64), ForeignKey("topology_validations.validation_id"), nullable=False, index=True)
    check_id: Mapped[str] = mapped_column(String(32), nullable=False)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    property_id: Mapped[str] = mapped_column(String(64), nullable=False)
    related_property_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    measured_value: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_condition: Mapped[str] = mapped_column(String(255), nullable=False)
    processing_method: Mapped[str] = mapped_column(String(128), default="Rule-Based 3D Cadastral Topology Validation", nullable=False)
    data_classification: Mapped[str] = mapped_column(String(128), default="Prototype Cadastral Data", nullable=False)

    # Relationships
    validation: Mapped["TopologyValidationModel"] = relationship("TopologyValidationModel", back_populates="checks")
