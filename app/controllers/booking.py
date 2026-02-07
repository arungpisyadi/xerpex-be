"""
Booking controller for the XerpeX ERP System
"""
from datetime import date
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingStatusUpdate,
    Booking, BookingDetail, BookingListResponse,
    BookingItemCreate, BookingItemUpdate, BookingItem,
    BookingVillaCreate, BookingVilla,
    BookingHistory, BookingStatus
)
from app.services.booking import (
    get_booking, get_bookings, create_booking, update_booking,
    update_booking_status, delete_booking,
    add_booking_item, update_booking_item, remove_booking_item,
    add_booking_villa, update_booking_villa, remove_booking_villa,
    get_booking_history, get_booking_statistics
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=BookingListResponse)
async def list_bookings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(999999, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by booking status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    search: Optional[str] = Query(None, description="Search by booking code or customer name"),
    check_in_from: Optional[str] = Query(None, description="Filter by check-in date from"),
    check_in_to: Optional[str] = Query(None, description="Filter by check-in date to"),
    villa_id: Optional[int] = Query(None, description="Filter by villa ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get list of bookings with optional filtering and search
    """
    # Convert empty strings to None
    status = status if status and status.strip() else None
    search = search if search and search.strip() else None
    check_in_from = check_in_from if check_in_from and check_in_from.strip() else None
    check_in_to = check_in_to if check_in_to and check_in_to.strip() else None
    
    # Validate and convert status to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = BookingStatus(status.lower())
        except ValueError:
            valid_statuses = [s.value for s in BookingStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status value. Must be one of: {', '.join(valid_statuses)}"
            )
    
    # Parse and validate dates if provided
    check_in_from_date = None
    check_in_to_date = None
    if check_in_from:
        try:
            check_in_from_date = date.fromisoformat(check_in_from)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid check_in_from date format. Use YYYY-MM-DD"
            )
    if check_in_to:
        try:
            check_in_to_date = date.fromisoformat(check_in_to)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid check_in_to date format. Use YYYY-MM-DD"
            )
    
    bookings = get_bookings(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        status=status_enum,
        customer_id=customer_id,
        search=search,
        check_in_from=check_in_from_date,
        check_in_to=check_in_to_date,
        villa_id=villa_id
    )
    
    # Get total count for pagination
    total_bookings = len(get_bookings(
        db=db,
        current_user=current_user,
        skip=0,
        limit=10000,
        status=status_enum,
        customer_id=customer_id,
        search=search,
        check_in_from=check_in_from_date,
        check_in_to=check_in_to_date,
        villa_id=villa_id
    ))
    
    return {
        "bookings": bookings,
        "total": total_bookings,
        "skip": skip,
        "limit": limit
    }


@router.post("", response_model=Booking, status_code=status.HTTP_201_CREATED)
async def create_booking_endpoint(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new booking with items and villas
    """
    try:
        db_booking = create_booking(
            db=db,
            booking=booking,
            current_user=current_user
        )
        return db_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/statistics", response_model=dict)
async def get_booking_statistics_endpoint(
    from_date: Optional[str] = Query(None, description="Statistics from date"),
    to_date: Optional[str] = Query(None, description="Statistics to date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get booking statistics for dashboard
    """
    # Convert empty strings to None
    from_date = from_date if from_date and from_date.strip() else None
    to_date = to_date if to_date and to_date.strip() else None
    
    # Parse and validate dates if provided
    from_date_obj = None
    to_date_obj = None
    if from_date:
        try:
            from_date_obj = date.fromisoformat(from_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid from_date format. Use YYYY-MM-DD"
            )
    if to_date:
        try:
            to_date_obj = date.fromisoformat(to_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid to_date format. Use YYYY-MM-DD"
            )
    
    stats = get_booking_statistics(
        db=db,
        current_user=current_user,
        from_date=from_date_obj,
        to_date=to_date_obj
    )
    return stats


@router.get("/create", response_model=dict)
async def get_create_booking_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get data needed for creating a booking (customers, villas, packages)
    """
    from app.services.customer import get_customers
    from app.services.villa import get_villas
    from app.services.package import get_packages
    
    # Fetch customers for dropdown
    customers = get_customers(db=db, current_user=current_user, skip=0, limit=1000)
    
    # Fetch active villas for selection
    villas = get_villas(db=db, skip=0, limit=1000, is_active=True)
    
    # Fetch packages for selection
    packages = get_packages(db=db, user_id=None, skip=0, limit=1000)
    
    return {
        "customers": [{"id": c.id, "name": c.name, "email": c.email, "phone_number": c.phone_number} for c in customers],
        "villas": [{"id": v.id, "name": v.name, "room_type": v.room_type, "capacity": v.capacity, "base_price": float(v.base_price)} for v in villas],
        "packages": [{"id": p.id, "name": p.name, "category": p.category, "type": p.type, "cost_per_pax": float(p.cost_per_pax), "days": p.days} for p in packages]
    }


@router.get("/{booking_id}", response_model=Booking)
async def get_booking_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific booking by ID
    """
    booking = get_booking(db=db, booking_id=booking_id, current_user=current_user)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    return booking


@router.put("/{booking_id}", response_model=Booking)
async def update_booking_endpoint(
    booking_id: int,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a booking
    """
    try:
        updated_booking = update_booking(
            db=db,
            booking_id=booking_id,
            booking_update=booking_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{booking_id}/status", response_model=Booking)
async def update_booking_status_endpoint(
    booking_id: int,
    status_update: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update booking status with workflow validation
    """
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_booking_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a booking (only pending or cancelled bookings)
    """
    success = delete_booking(
        db=db,
        booking_id=booking_id,
        current_user=current_user
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )


# ============================================================================
# Booking Items Management
# ============================================================================

@router.post("/{booking_id}/items", response_model=BookingItem, status_code=status.HTTP_201_CREATED)
async def add_booking_item_endpoint(
    booking_id: int,
    item: BookingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add an item to a booking
    """
    try:
        booking_item = add_booking_item(
            db=db,
            booking_id=booking_id,
            item=item,
            current_user=current_user
        )
        return booking_item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{booking_id}/items/{item_id}", response_model=BookingItem)
async def update_booking_item_endpoint(
    booking_id: int,
    item_id: int,
    item_update: BookingItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a booking item
    """
    try:
        updated_item = update_booking_item(
            db=db,
            booking_id=booking_id,
            item_id=item_id,
            item_update=item_update,
            current_user=current_user
        )
        return updated_item
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{booking_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_booking_item_endpoint(
    booking_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove an item from a booking
    """
    success = remove_booking_item(
        db=db,
        booking_id=booking_id,
        item_id=item_id,
        current_user=current_user
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking item not found"
        )


# ============================================================================
# Villa Management
# ============================================================================

@router.post("/{booking_id}/villas", response_model=BookingVilla, status_code=status.HTTP_201_CREATED)
async def add_villa_to_booking(
    booking_id: int,
    villa_data: BookingVillaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a villa to a booking
    """
    try:
        booking_villa = add_booking_villa(
            db=db,
            booking_id=booking_id,
            villa=villa_data,
            current_user=current_user
        )
        return booking_villa
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{booking_id}/villas/{villa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_villa_from_booking(
    booking_id: int,
    villa_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a villa from a booking
    """
    success = remove_booking_villa(
        db=db,
        booking_id=booking_id,
        villa_id=villa_id,
        current_user=current_user
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found in booking"
        )


# ============================================================================
# Booking History
# ============================================================================

@router.get("/{booking_id}/history", response_model=List[BookingHistory])
async def get_booking_history_endpoint(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get booking change history
    """
    history = get_booking_history(
        db=db,
        booking_id=booking_id,
        current_user=current_user
    )
    return history


# ============================================================================
# Booking Workflow Actions
# ============================================================================

@router.post("/{booking_id}/confirm", response_model=Booking)
async def confirm_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirm a booking (change status from pending to confirmed)
    """
    status_update = BookingStatusUpdate(status=BookingStatus.confirmed)
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{booking_id}/check-in", response_model=Booking)
async def check_in_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check in a booking (change status to checked_in)
    """
    status_update = BookingStatusUpdate(status=BookingStatus.checked_in)
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{booking_id}/check-out", response_model=Booking)
async def check_out_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Check out a booking (change status to checked_out)
    """
    status_update = BookingStatusUpdate(status=BookingStatus.checked_out)
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{booking_id}/complete", response_model=Booking)
async def complete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete a booking (change status to completed)
    """
    status_update = BookingStatusUpdate(status=BookingStatus.completed)
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{booking_id}/cancel", response_model=Booking)
async def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancel a booking (change status to cancelled)
    """
    status_update = BookingStatusUpdate(status=BookingStatus.cancelled)
    try:
        updated_booking = update_booking_status(
            db=db,
            booking_id=booking_id,
            status_update=status_update,
            current_user=current_user
        )
        return updated_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )