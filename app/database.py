"""
Database connection and session management for the XerpeX ERP System
"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

# Create SQLAlchemy engine with optimized timeout settings
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=False,
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=120,   # Increased from 30 seconds to 120 seconds
    pool_size=10,       # Explicitly set pool size
    max_overflow=20,    # Allow up to 20 connections beyond pool_size
    connect_args={
        "connect_timeout": 60,  # Increased from 10 seconds to 60 seconds
        "read_timeout": 300,    # Add read timeout of 5 minutes
        "write_timeout": 300    # Add write timeout of 5 minutes
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting a database session
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()