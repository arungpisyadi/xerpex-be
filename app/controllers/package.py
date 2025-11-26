"""
Package controllers for the XerpeX ERP System
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.package import Package, PackageCreate, PackageUpdate
from app.services.package import (
    get_package, get_packages, create_package, update_package, delete_package,
    get_package_categories, get_package_types
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=List[Package])
async def read_packages(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    min_cost: Optional[float] = Query(None, description="Filter by minimum cost per pax"),
    max_cost: Optional[float] = Query(None, description="Filter by maximum cost per pax"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all packages with optional filtering and search (no user isolation)
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Filter by category
        type: Filter by type
        min_cost: Filter by minimum cost per pax
        max_cost: Filter by maximum cost per pax
        search: Search by name (partial match)
        db: Database session
        current_user: Current user (required for authentication)
        
    Returns:
        List[Package]: List of all packages visible to all users
    """
    packages = get_packages(
        db,
        skip=skip,
        limit=limit,
        category=category,
        type=type,
        min_cost=min_cost,
        max_cost=max_cost,
        search=search
    )
    return packages


@router.post("", response_model=Package, status_code=status.HTTP_201_CREATED)
async def create_new_package(
    package: PackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new package with user isolation
    
    Args:
        package: Package data
        db: Database session
        current_user: Current user
        
    Returns:
        Package: Created package
    """
    return create_package(db=db, package=package, user_id=current_user.id)


@router.get("/{package_id}", response_model=Package)
async def read_package(
    package_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a package by ID (no user isolation)
    
    Args:
        package_id: Package ID
        db: Database session
        current_user: Current user (required for authentication)
        
    Returns:
        Package: Package
        
    Raises:
        HTTPException: If package not found
    """
    db_package = get_package(db, package_id=package_id)
    if db_package is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found"
        )
    
    return db_package


@router.put("/{package_id}", response_model=Package)
async def update_package_endpoint(
    package_id: int,
    package_update: PackageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a package with user isolation
    
    Args:
        package_id: Package ID
        package_update: Package update data
        db: Database session
        current_user: Current user
        
    Returns:
        Package: Updated package
        
    Raises:
        HTTPException: If package not found
    """
    return update_package(db=db, package_id=package_id, package_update=package_update, user_id=current_user.id)


@router.delete("/{package_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_package_endpoint(
    package_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a package with user isolation
    
    Args:
        package_id: Package ID
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If package not found
    """
    delete_package(db=db, package_id=package_id, user_id=current_user.id)
    return None


@router.get("/meta/categories", response_model=List[str])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all unique package categories (no user isolation)
    
    Args:
        db: Database session
        current_user: Current user (required for authentication)
        
    Returns:
        List[str]: List of unique categories from all packages
    """
    return get_package_categories(db)


@router.get("/meta/types", response_model=List[str])
async def get_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all unique package types (no user isolation)
    
    Args:
        db: Database session
        current_user: Current user (required for authentication)
        
    Returns:
        List[str]: List of unique types from all packages
    """
    return get_package_types(db)