"""
Package services for the XerpeX ERP System
"""
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.package import Package
from app.schemas.package import PackageCreate, PackageUpdate


def get_package(db: Session, package_id: int, user_id: Optional[int] = None) -> Optional[Package]:
    """
    Get a package by ID with optional user isolation
    
    Args:
        db: Database session
        package_id: Package ID
        user_id: Optional user ID for isolation
        
    Returns:
        Package: Package or None
    """
    query = db.query(Package).filter(Package.id == package_id)
    if user_id is not None:
        query = query.filter(Package.user_id == user_id)
    return query.first()


def get_packages(
    db: Session,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    type: Optional[str] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    search: Optional[str] = None
) -> List[Package]:
    """
    Get packages with optional filtering and search
    
    Args:
        db: Database session
        user_id: Optional user ID for isolation
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Filter by category
        type: Filter by type
        min_cost: Filter by minimum cost per pax
        max_cost: Filter by maximum cost per pax
        search: Search by name (partial match)
        
    Returns:
        List[Package]: List of packages
    """
    query = db.query(Package)
    
    # Apply user isolation if provided
    if user_id is not None:
        query = query.filter(Package.user_id == user_id)
    
    # Apply filters
    if category:
        query = query.filter(Package.category == category)
    
    if type:
        query = query.filter(Package.type == type)
    
    if min_cost is not None:
        query = query.filter(Package.cost_per_pax >= min_cost)
    
    if max_cost is not None:
        query = query.filter(Package.cost_per_pax <= max_cost)
    
    if search:
        query = query.filter(Package.name.ilike(f"%{search}%"))
    
    return query.offset(skip).limit(limit).all()


def create_package(db: Session, package: PackageCreate, user_id: int) -> Package:
    """
    Create a new package with user isolation
    
    Args:
        db: Database session
        package: Package data
        user_id: User ID for isolation
        
    Returns:
        Package: Created package
    """
    db_package = Package(
        user_id=user_id,
        name=package.name,
        category=package.category,
        type=package.type,
        description=package.description,
        days=package.days,
        cost_per_pax=package.cost_per_pax,
        min_pax=package.min_pax,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_package)
    db.commit()
    db.refresh(db_package)
    
    return db_package


def update_package(db: Session, package_id: int, package_update: PackageUpdate, user_id: int) -> Package:
    """
    Update a package with user isolation
    
    Args:
        db: Database session
        package_id: Package ID
        package_update: Package update data
        user_id: User ID for isolation
        
    Returns:
        Package: Updated package
        
    Raises:
        HTTPException: If package not found
    """
    db_package = get_package(db, package_id, user_id)
    if not db_package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    # Update package fields
    update_data = package_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_package, key, value)
    
    db_package.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_package)
    
    return db_package


def delete_package(db: Session, package_id: int, user_id: int) -> bool:
    """
    Delete a package with user isolation
    
    Args:
        db: Database session
        package_id: Package ID
        user_id: User ID for isolation
        
    Returns:
        bool: True if package was deleted
        
    Raises:
        HTTPException: If package not found
    """
    db_package = get_package(db, package_id, user_id)
    if not db_package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    db.delete(db_package)
    db.commit()
    
    return True


def get_package_categories(db: Session, user_id: Optional[int] = None) -> List[str]:
    """
    Get all unique package categories with optional user isolation
    
    Args:
        db: Database session
        user_id: Optional user ID for isolation
        
    Returns:
        List[str]: List of unique categories
    """
    query = db.query(Package.category).filter(Package.category.isnot(None))
    if user_id is not None:
        query = query.filter(Package.user_id == user_id)
    categories = query.distinct().all()
    return [category[0] for category in categories]


def get_package_types(db: Session, user_id: Optional[int] = None) -> List[str]:
    """
    Get all unique package types with optional user isolation
    
    Args:
        db: Database session
        user_id: Optional user ID for isolation
        
    Returns:
        List[str]: List of unique types
    """
    query = db.query(Package.type).filter(Package.type.isnot(None))
    if user_id is not None:
        query = query.filter(Package.user_id == user_id)
    types = query.distinct().all()
    return [type_[0] for type_ in types]