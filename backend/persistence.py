"""
GeoCadastre-3D Persistence & Repository Service Layer (Day 6 Step 3)
Encapsulates controlled CRUD and transactional database operations for
Parcels, Properties (3D Volumetric Units), LiDAR Surveys, Spatial Conflicts,
and Cadastral Topology Validations.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from db_models import (
    ParcelModel,
    PropertyModel,
    LidarSurveyModel,
    ConflictModel,
    TopologyValidationModel,
    TopologyCheckModel
)


# =========================================================================
# PARCEL PERSISTENCE REPOSITORY
# =========================================================================

def get_parcel(db: Session, parcel_id: str) -> Optional[ParcelModel]:
    """Retrieves a single parcel by primary key or case-insensitive match."""
    return db.query(ParcelModel).filter(
        (func.lower(ParcelModel.parcel_id) == parcel_id.lower()) |
        (ParcelModel.parcel_id == parcel_id)
    ).first()


def get_all_parcels(db: Session) -> List[ParcelModel]:
    """Retrieves all registered base 2D cadastral parcels."""
    return db.query(ParcelModel).all()


def create_parcel(db: Session, parcel_data: Dict[str, Any]) -> ParcelModel:
    """Creates and commits a new cadastral base parcel record."""
    parcel = ParcelModel(**parcel_data)
    db.add(parcel)
    db.commit()
    db.refresh(parcel)
    return parcel


def update_parcel(db: Session, parcel_id: str, updates: Dict[str, Any]) -> Optional[ParcelModel]:
    """Updates an existing parcel's attributes in place."""
    parcel = get_parcel(db, parcel_id)
    if not parcel:
        return None
    for key, value in updates.items():
        if hasattr(parcel, key):
            setattr(parcel, key, value)
    db.commit()
    db.refresh(parcel)
    return parcel


def delete_parcel(db: Session, parcel_id: str) -> bool:
    """Deletes a parcel and cascades to child volumetric property units."""
    parcel = get_parcel(db, parcel_id)
    if not parcel:
        return False
    db.delete(parcel)
    db.commit()
    return True


# =========================================================================
# PROPERTY / VOLUMETRIC UNIT PERSISTENCE REPOSITORY
# =========================================================================

def get_property(db: Session, property_id: str) -> Optional[PropertyModel]:
    """Retrieves a single property by primary key or case-insensitive match."""
    return db.query(PropertyModel).filter(
        (func.lower(PropertyModel.property_id) == property_id.lower()) |
        (PropertyModel.property_id == property_id)
    ).first()


def get_property_by_ulpin(db: Session, ulpin: str) -> Optional[PropertyModel]:
    """Retrieves a single property by authoritative 3D ULPIN."""
    return db.query(PropertyModel).filter(PropertyModel.ulpin == ulpin).first()


def get_all_properties(db: Session) -> List[PropertyModel]:
    """Retrieves all registered 3D cadastral property volumes."""
    return db.query(PropertyModel).all()


def get_properties_for_parcel(db: Session, parcel_id: str) -> List[PropertyModel]:
    """Retrieves all 3D volumetric properties registered under a base parcel."""
    return db.query(PropertyModel).filter(
        (func.lower(PropertyModel.parcel_id) == parcel_id.lower()) |
        (PropertyModel.parcel_id == parcel_id)
    ).all()


def create_property(db: Session, property_data: Dict[str, Any]) -> PropertyModel:
    """Creates and commits a new 3D volumetric property unit."""
    prop = PropertyModel(**property_data)
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


def update_property(db: Session, property_id: str, updates: Dict[str, Any]) -> Optional[PropertyModel]:
    """Updates an existing property unit's attributes."""
    prop = get_property(db, property_id)
    if not prop:
        return None
    for key, value in updates.items():
        if hasattr(prop, key):
            setattr(prop, key, value)
    db.commit()
    db.refresh(prop)
    return prop


def delete_property(db: Session, property_id: str) -> bool:
    """Deletes an individual property unit."""
    prop = get_property(db, property_id)
    if not prop:
        return False
    db.delete(prop)
    db.commit()
    return True


# =========================================================================
# LIDAR SURVEY METADATA PERSISTENCE REPOSITORY
# =========================================================================

def get_lidar_survey(db: Session, survey_id: str = "LS-BLR-2026-001") -> Optional[LidarSurveyModel]:
    """Retrieves LiDAR survey metadata record."""
    return db.query(LidarSurveyModel).filter(LidarSurveyModel.survey_id == survey_id).first()


def create_lidar_survey(db: Session, survey_data: Dict[str, Any]) -> LidarSurveyModel:
    """Creates and commits a new LiDAR survey metadata entry."""
    survey = LidarSurveyModel(**survey_data)
    db.add(survey)
    db.commit()
    db.refresh(survey)
    return survey


# =========================================================================
# 3D SPATIAL CONFLICT PERSISTENCE REPOSITORY
# =========================================================================

def get_conflict(db: Session, conflict_id: str) -> Optional[ConflictModel]:
    """Retrieves a specific spatial conflict dispute record."""
    return db.query(ConflictModel).filter(
        (func.lower(ConflictModel.conflict_id) == conflict_id.lower()) |
        (ConflictModel.conflict_id == conflict_id)
    ).first()


def get_all_conflicts(db: Session) -> List[ConflictModel]:
    """Retrieves all detected 3D spatial overlap conflicts."""
    return db.query(ConflictModel).all()


def get_conflicts_for_property(db: Session, property_id: str) -> List[ConflictModel]:
    """Retrieves all active conflicts where the specified property is a participant."""
    return db.query(ConflictModel).filter(
        (func.lower(ConflictModel.property_a) == property_id.lower()) |
        (func.lower(ConflictModel.property_b) == property_id.lower()) |
        (ConflictModel.property_a == property_id) |
        (ConflictModel.property_b == property_id)
    ).all()


def create_conflict(db: Session, conflict_data: Dict[str, Any]) -> ConflictModel:
    """Creates and commits a new spatial boundary overlap conflict."""
    conflict = ConflictModel(**conflict_data)
    db.add(conflict)
    db.commit()
    db.refresh(conflict)
    return conflict


def update_conflict(db: Session, conflict_id: str, updates: Dict[str, Any]) -> Optional[ConflictModel]:
    """Updates an existing spatial dispute's status or dimensions."""
    c = get_conflict(db, conflict_id)
    if not c:
        return None
    for key, value in updates.items():
        if hasattr(c, key):
            setattr(c, key, value)
    db.commit()
    db.refresh(c)
    return c


def delete_conflict(db: Session, conflict_id: str) -> bool:
    """Removes a resolved spatial conflict record."""
    c = get_conflict(db, conflict_id)
    if not c:
        return False
    db.delete(c)
    db.commit()
    return True


# =========================================================================
# 3D CADASTRAL TOPOLOGY VALIDATION PERSISTENCE REPOSITORY
# =========================================================================

def get_topology_validation(db: Session, property_id: str) -> Optional[TopologyValidationModel]:
    """Retrieves topology validation audit for a single property with associated checks."""
    return db.query(TopologyValidationModel).filter(
        (func.lower(TopologyValidationModel.property_id) == property_id.lower()) |
        (TopologyValidationModel.property_id == property_id)
    ).first()


def get_all_topology_validations(db: Session) -> List[TopologyValidationModel]:
    """Retrieves all property topology validation audits with their checks."""
    return db.query(TopologyValidationModel).all()


def create_topology_validation(
    db: Session,
    validation_data: Dict[str, Any],
    checks_data: List[Dict[str, Any]]
) -> TopologyValidationModel:
    """Creates a topology validation transaction along with its granular rule evaluations."""
    validation = TopologyValidationModel(**validation_data)
    db.add(validation)
    db.flush()

    for chk in checks_data:
        chk_record = TopologyCheckModel(
            validation_id=validation.validation_id,
            **chk
        )
        db.add(chk_record)

    db.commit()
    db.refresh(validation)
    return validation


def delete_topology_validation(db: Session, validation_id: str) -> bool:
    """Deletes a topology validation record and cascades to its checks."""
    val = db.query(TopologyValidationModel).filter(
        TopologyValidationModel.validation_id == validation_id
    ).first()
    if not val:
        return False
    db.delete(val)
    db.commit()
    return True
