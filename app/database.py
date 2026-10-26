"""Database connection and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Database URL - use SQLite for local development
# Can be overridden with DATABASE_URL environment variable for PostgreSQL, etc.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./aml_reviews.db"
)

# Create engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
        echo=False,  # Set to True for SQL query logging
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(DATABASE_URL, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def init_db():
    """Initialize the database - create all tables."""
    from app.models_db import AMLReview  # Import here to avoid circular imports
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get a database session (dependency for FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session():
    """Context manager for database sessions (for use outside FastAPI)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
