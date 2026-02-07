"""
Villa controllers for the XerpeX ERP System
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.villa import (
    Villa, VillaCreate, VillaUpdate, VillaWithAvailability,
    VillaAvailability, VillaAvailabilityCreate, VillaAvailabilityUpdate,
    AvailabilityCheck, AvailabilityResponse, VillaListResponse
)
from app.services.villa import (
    get_villa, get_villas, create_villa, update_villa, delete_villa,
    get_villa_availability, create_villa_availability, update_villa_availability,
    check_villa_availability, get_available_villas
)
from app.utils.security import get_current_active_user

router = APIRouter(prefix="/villas", tags=["villas"])


@router.get("", response_model=List[Villa])
async def read_villas(
    skip: int = 0,
    limit: int = 999999,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    room_type: Optional[str] = Query(None, description="Filter by room type"),
    min_capacity: Optional[str] = Query(None, description="Filter by minimum capacity"),
    db: Session = Depends(get_db)
):
    """
    Get all villas with optional filtering
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        room_type: Filter by room type
        min_capacity: Filter by minimum capacity
        db: Database session
        
    Returns:
        List[Villa]: List of villas
    """
    villas = get_villas(
        db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        room_type=room_type,
        min_capacity=min_capacity
    )
    return villas


@router.get("/available", response_model=VillaListResponse)
async def get_available_villas_endpoint(
    check_in: date = Query(..., description="Check-in date"),
    check_out: date = Query(..., description="Check-out date"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    name: Optional[str] = Query(None, description="Filter by villa name (partial match)"),
    db: Session = Depends(get_db)
):
    """
    Get available villas for a date range.
    
    Returns all villas that are available (not blocked) for the entire period
    between check_in and check_out dates. Villas with any unavailable dates
    in this range will be excluded from the results.
    
    Args:
        check_in: Start date of the availability check
        check_out: End date of the availability check (must be on or after check_in)
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        is_active: Filter by active status
        location: Filter by location (case-insensitive partial match)
        name: Filter by villa name (case-insensitive partial match)
        db: Database session
    
    Returns:
        VillaListResponse containing list of available villas and pagination info
        
    Raises:
        HTTPException: 400 if check_out is before check_in
    """
    # Validate dates
    if check_out < check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="check_out cannot be before check_in"
        )
    
    # Get available villas
    villas, total = get_available_villas(
        db=db,
        check_in=check_in,
        check_out=check_out,
        skip=skip,
        limit=limit,
        is_active=is_active,
        location=location,
        name=name
    )
    
    return {
        "villas": villas,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=Villa, status_code=status.HTTP_201_CREATED)
async def create_new_villa(
    villa: VillaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new villa
    
    Args:
        villa: Villa data
        db: Database session
        current_user: Current user
        
    Returns:
        Villa: Created villa
        
    Raises:
        HTTPException: If not enough permissions
    """
    # Only admin and manager can create villas
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return create_villa(db=db, villa=villa)


@router.get("/{villa_id}", response_model=VillaWithAvailability)
async def read_villa(
    villa_id: int,
    start_date: Optional[date] = Query(None, description="Start date for availability"),
    end_date: Optional[date] = Query(None, description="End date for availability"),
    db: Session = Depends(get_db)
):
    """
    Get a villa by ID with optional availability
    
    Args:
        villa_id: Villa ID
        start_date: Start date for availability
        end_date: End date for availability
        db: Database session
        
    Returns:
        VillaWithAvailability: Villa with availability
        
    Raises:
        HTTPException: If villa not found
    """
    db_villa = get_villa(db, villa_id=villa_id)
    if db_villa is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    # Get availability if date range is provided
    if start_date and end_date:
        availabilities = get_villa_availability(db, villa_id, start_date, end_date)
        db_villa.availabilities = availabilities
    
    return db_villa


@router.put("/{villa_id}", response_model=Villa)
async def update_villa_endpoint(
    villa_id: int,
    villa_update: VillaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a villa
    
    Args:
        villa_id: Villa ID
        villa_update: Villa update data
        db: Database session
        current_user: Current user
        
    Returns:
        Villa: Updated villa
        
    Raises:
        HTTPException: If villa not found or not enough permissions
    """
    # Only admin and manager can update villas
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return update_villa(db=db, villa_id=villa_id, villa_update=villa_update)


@router.delete("/{villa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_villa_endpoint(
    villa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a villa
    
    Args:
        villa_id: Villa ID
        db: Database session
        current_user: Current user
        
    Raises:
        HTTPException: If villa not found or not enough permissions
    """
    # Only admin can delete villas
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    delete_villa(db=db, villa_id=villa_id)
    return None


@router.post("/availability", response_model=VillaAvailability)
async def create_villa_availability_endpoint(
    availability: VillaAvailabilityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new villa availability
    
    Args:
        availability: Villa availability data
        db: Database session
        current_user: Current user
        
    Returns:
        VillaAvailability: Created villa availability
        
    Raises:
        HTTPException: If villa not found, availability already exists, or not enough permissions
    """
    # Only admin, manager, and staff can create villa availability
    if current_user.role not in ["admin", "manager", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return create_villa_availability(db=db, availability=availability, current_user_id=current_user.id)


@router.put("/{villa_id}/availability/{date}", response_model=VillaAvailability)
async def update_villa_availability_endpoint(
    villa_id: int,
    date: date,
    availability_update: VillaAvailabilityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a villa availability
    
    Args:
        villa_id: Villa ID
        date: Date
        availability_update: Villa availability update data
        db: Database session
        current_user: Current user
        
    Returns:
        VillaAvailability: Updated villa availability
        
    Raises:
        HTTPException: If villa not found or not enough permissions
    """
    # Only admin, manager, and staff can update villa availability
    if current_user.role not in ["admin", "manager", "staff"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return update_villa_availability(
        db=db, 
        villa_id=villa_id, 
        date_value=date, 
        availability_update=availability_update, 
        current_user_id=current_user.id
    )


@router.post("/check-availability", response_model=AvailabilityResponse)
async def check_availability_endpoint(
    check: AvailabilityCheck,
    db: Session = Depends(get_db)
):
    """
    Check if a villa is available for a date range
    
    Args:
        check: Availability check data
        db: Database session
        
    Returns:
        AvailabilityResponse: Availability response
        
    Raises:
        HTTPException: If villa not found
    """
    is_available, unavailable_dates = check_villa_availability(
        db=db, 
        villa_id=check.villa_id, 
        check_in=check.check_in, 
        check_out=check.check_out
    )
    
    return AvailabilityResponse(
        is_available=is_available,
        villa_id=check.villa_id,
        unavailable_dates=unavailable_dates
    )
