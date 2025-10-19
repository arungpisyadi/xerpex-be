"""
Villa services for the XerpeX ERP System
"""
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.villa import Villa, VillaAvailability
from app.schemas.villa import VillaCreate, VillaUpdate, VillaAvailabilityCreate, VillaAvailabilityUpdate
def get_villa(db: Session, villa_id: int) -> Optional[Villa]:
    """
    Get a villa by ID
    
    Args:
        db: Database session
        villa_id: Villa ID
        
    Returns:
        Villa: Villa or None
    """
    return db.query(Villa).filter(Villa.id == villa_id).first()


def get_villas(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    is_active: Optional[bool] = None,
    room_type: Optional[str] = None,
    min_capacity: Optional[str] = None
) -> List[Villa]:
    """
    Get villas with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        room_type: Filter by room type
        min_capacity: Filter by minimum capacity (as string)
        
    Returns:
        List[Villa]: List of villas
    """
    query = db.query(Villa)
    
    if is_active is not None:
        query = query.filter(Villa.is_active == is_active)
    
    if room_type:
        query = query.filter(Villa.room_type == room_type)
    
    if min_capacity:
        query = query.filter(Villa.capacity >= min_capacity)
    
    return query.offset(skip).limit(limit).all()


def create_villa(db: Session, villa: VillaCreate) -> Villa:
    """
    Create a new villa
    
    Args:
        db: Database session
        villa: Villa data
        
    Returns:
        Villa: Created villa
    """
    db_villa = Villa(
        name=villa.name,
        description=villa.description,
        capacity=villa.capacity,
        room_type=villa.room_type,
        base_price=villa.base_price,
        is_active=villa.is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_villa)
    db.commit()
    db.refresh(db_villa)
    
    return db_villa


def update_villa(db: Session, villa_id: int, villa_update: VillaUpdate) -> Villa:
    """
    Update a villa
    
    Args:
        db: Database session
        villa_id: Villa ID
        villa_update: Villa update data
        
    Returns:
        Villa: Updated villa
        
    Raises:
        HTTPException: If villa not found
    """
    db_villa = get_villa(db, villa_id)
    if not db_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    # Update villa fields
    update_data = villa_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_villa, key, value)
    
    db_villa.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_villa)
    
    return db_villa


def delete_villa(db: Session, villa_id: int) -> bool:
    """
    Delete a villa
    
    Args:
        db: Database session
        villa_id: Villa ID
        
    Returns:
        bool: True if villa was deleted
        
    Raises:
        HTTPException: If villa not found
    """
    db_villa = get_villa(db, villa_id)
    if not db_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    db.delete(db_villa)
    db.commit()
    
    return True


def get_villa_availability(
    db: Session, 
    villa_id: int, 
    start_date: date, 
    end_date: date
) -> List[VillaAvailability]:
    """
    Get villa availability for a date range
    
    Args:
        db: Database session
        villa_id: Villa ID
        start_date: Start date
        end_date: End date
        
    Returns:
        List[VillaAvailability]: List of villa availabilities
        
    Raises:
        HTTPException: If villa not found
    """
    db_villa = get_villa(db, villa_id)
    if not db_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    return db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.date >= start_date,
        VillaAvailability.date < end_date
    ).all()


def create_villa_availability(
    db: Session, 
    availability: VillaAvailabilityCreate, 
    current_user_id: int
) -> VillaAvailability:
    """
    Create a new villa availability
    
    Args:
        db: Database session
        availability: Villa availability data
        current_user_id: Current user ID
        
    Returns:
        VillaAvailability: Created villa availability
        
    Raises:
        HTTPException: If villa not found or availability already exists
    """
    db_villa = get_villa(db, availability.villa_id)
    if not db_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    # Check if availability already exists
    existing = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == availability.villa_id,
        VillaAvailability.date == availability.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Availability already exists for this date"
        )
    
    db_availability = VillaAvailability(
        villa_id=availability.villa_id,
        date=availability.date,
        is_available=availability.is_available,
        blocked_reason=availability.blocked_reason,
        updated_by=current_user_id,
        updated_at=datetime.utcnow()
    )
    
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)
    
    return db_availability


def update_villa_availability(
    db: Session, 
    villa_id: int, 
    date_value: date, 
    availability_update: VillaAvailabilityUpdate, 
    current_user_id: int
) -> VillaAvailability:
    """
    Update a villa availability
    
    Args:
        db: Database session
        villa_id: Villa ID
        date_value: Date
        availability_update: Villa availability update data
        current_user_id: Current user ID
        
    Returns:
        VillaAvailability: Updated villa availability
        
    Raises:
        HTTPException: If villa or availability not found
    """
    db_villa = get_villa(db, villa_id)
    if not db_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found"
        )
    
    db_availability = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.date == date_value
    ).first()
    
    if not db_availability:
        # Create new availability if it doesn't exist
        db_availability = VillaAvailability(
            villa_id=villa_id,
            date=date_value,
            updated_by=current_user_id,
            updated_at=datetime.utcnow()
        )
        db.add(db_availability)
    
    # Update availability fields
    update_data = availability_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_availability, key, value)
    
    db_availability.updated_by = current_user_id
    db_availability.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_availability)
    
    return db_availability


def check_villa_availability(
    db: Session, 
    villa_id: Optional[int], 
    check_in: date, 
    check_out: date
) -> Tuple[bool, Optional[List[date]]]:
    """
    Check if a villa is available for a date range
    
    Args:
        db: Database session
        villa_id: Villa ID (optional)
        check_in: Check-in date
        check_out: Check-out date
        
    Returns:
        Tuple[bool, Optional[List[date]]]: (is_available, unavailable_dates)
        
    Raises:
        HTTPException: If villa not found
    """
    if villa_id:
        db_villa = get_villa(db, villa_id)
        if not db_villa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Villa not found"
            )
    
    # Generate list of dates to check
    date_range = []
    current_date = check_in
    while current_date < check_out:
        date_range.append(current_date)
        current_date += timedelta(days=1)
    
    # Query for unavailable dates
    query = db.query(VillaAvailability).filter(
        VillaAvailability.date.in_(date_range),
        VillaAvailability.is_available == False
    )
    
    if villa_id:
        query = query.filter(VillaAvailability.villa_id == villa_id)
    
    unavailable = query.all()
    
    if unavailable:
        unavailable_dates = [item.date for item in unavailable]
        return False, unavailable_dates
    
    return True, None
