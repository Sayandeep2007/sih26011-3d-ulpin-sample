"""
GeoCadastre-3D Database Initialization Script (Day 6 Step 1B)
Non-destructive schema creation for SQLAlchemy 2.x ORM models.
"""

import sys
import os

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import engine, Base
import db_models  # Ensure all ORM models are registered with Base.metadata


def init_database() -> bool:
    """
    Initializes all database tables registered in Base.metadata.
    Non-destructive: Uses create_all() which creates tables only if they do not exist.
    Never drops existing tables.
    """
    print("=" * 60)
    print("GeoCadastre-3D Database Initialization")
    print(f"Engine Dialect: {engine.dialect.name}")
    print(f"Target Database: {engine.url}")
    print("=" * 60)

    try:
        # Create all tables non-destructively
        Base.metadata.create_all(bind=engine)
        
        tables = list(Base.metadata.tables.keys())
        print(f"SUCCESS: Successfully verified/created {len(tables)} tables:")
        for tbl in sorted(tables):
            print(f"  - {tbl}")
        print("=" * 60)
        return True
    except Exception as e:
        print(f"ERROR: Database initialization failed: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
