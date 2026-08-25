"""
GeoCadastre-3D Database Configuration Module (Day 6 Step 5 Hardened)
SQLAlchemy 2.x persistence layer with PostgreSQL readiness, SQLite local fallback,
connection pooling safeguards, and robust environment configuration.
"""

import os
from typing import Generator, Dict, Any
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

# Default fallback SQLite database path
DEFAULT_SQLITE_URL = "sqlite:///./geocadastre3d.db"

# Retrieve and sanitize DATABASE_URL
raw_db_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = raw_db_url if raw_db_url else DEFAULT_SQLITE_URL

# Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy 2.x
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configure dialect-specific engine parameters
connect_args: Dict[str, Any] = {}
engine_kwargs: Dict[str, Any] = {
    "pool_pre_ping": True,
    "future": True,
    "echo": False
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 30
    engine_kwargs["connect_args"] = connect_args
elif DATABASE_URL.startswith("postgresql"):
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20
    engine_kwargs["pool_recycle"] = 1800
    engine_kwargs["pool_timeout"] = 30

# SQLAlchemy 2.x Engine instance
engine: Engine = create_engine(
    DATABASE_URL,
    **engine_kwargs
)

# Thread-safe Session Factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# SQLAlchemy 2.0 Declarative Base Class
class Base(DeclarativeBase):
    """Declarative Base class for all GeoCadastre-3D database models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency yielding a database session per request.
    Ensures proper cleanup and closing on completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
