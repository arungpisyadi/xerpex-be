"""
Booking services for the XerpeX ERP System
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingVilla, BookingPackage, BookingAddon
from app.models.payment import Payment
from app.models.villa import Villa, VillaAvailability
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingStatusUpdate,
    BookingVillaCreate, BookingPackageCreate, BookingAddonCreate
)
from app.services.villa import get_villa, check_villa_availability
from app.utils.helpers import generate_booking_code, calculate_nights
def get_booking(db: Session, booking_id: int) -> Optional[Booking]:
    """
    Get a booking by ID
    
    Args:
        db: Database session
        booking_id: Booking ID
        
    Returns:
        Booking: Booking or None
    """
    return db.query(Booking).filter(Booking.id == booking_id).first()


def get_booking_by_code(db: Session, booking_code: str) -> Optional[Booking]:
    """
    Get a booking by code
    
    Args:
        db: Database session
        booking_code: Booking code
        
    Returns:
        Booking: Booking or None
    """
    return db.query(Booking).filter(Booking.booking_code == booking_code).first()


def get_bookings(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    guest_name: Optional[str] = None,
    check_in_from: Optional[date] = None,
    check_in_to: Optional[date] = None,
    villa_id: Optional[int] = None
) -> List[Booking]:
    """
    Get bookings with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        guest_name: Filter by guest name
        check_in_from: Filter by check-in date from
        check_in_to: Filter by check-in date to
        villa_id: Filter by villa ID
        
    Returns:
        List[Booking]: List of bookings
    """
    query = db.query(Booking)
    
    if status:
        query = query.filter(Booking.status == status)
    
    if guest_name:
        query = query.filter(Booking.guest_name.ilike(f"%{guest_name}%"))
    
    if check_in_from:
        query = query.filter(Booking.check_in >= check_in_from)
    
    if check_in_to:
        query = query.filter(Booking.check_in <= check_in_to)
    
    if villa_id:
        query = query.join(BookingVilla).filter(BookingVilla.villa_id == villa_id)
    
    return query.order_by(Booking.created_at.desc()).offset(skip).limit(limit).all()


def create_booking(db: Session, booking: BookingCreate, current_user_id: int) -> Booking:
    """
    Create a new booking
    
    Args:
        db: Database session
        booking: Booking data
        current_user_id: Current user ID
        
    Returns:
        Booking: Created booking
        
    Raises:
        HTTPException: If villa not found or not available
    """
    # Check if villas exist and are available
    for villa_data in booking.villas:
        villa = get_villa(db, villa_data.villa_id)
        if not villa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Villa with ID {villa_data.villa_id} not found"
            )
        
        # Check availability
        is_available, unavailable_dates = check_villa_availability(
            db, villa_data.villa_id, booking.check_in, booking.check_out
        )
        
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Villa with ID {villa_data.villa_id} is not available for the selected dates"
            )
    
    # Create booking
    booking_code = generate_booking_code()
    db_booking = Booking(
        booking_code=booking_code,
        guest_name=booking.guest_name,
        guest_email=booking.guest_email,
        guest_phone=booking.guest_phone,
        check_in=booking.check_in,
        check_out=booking.check_out,
        total_pax=booking.total_pax,
        status="pending",
        notes=booking.notes,
        created_by=current_user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    # Add villas to booking
    for villa_data in booking.villas:
        db_booking_villa = BookingVilla(
            booking_id=db_booking.id,
            villa_id=villa_data.villa_id,
            assigned_at=datetime.utcnow()
        )
        db.add(db_booking_villa)
    
    # Add packages to booking if provided
    if booking.packages:
        for package_data in booking.packages:
            db_booking_package = BookingPackage(
                booking_id=db_booking.id,
                package_name=package_data.package_name,
                package_price=package_data.package_price,
                notes=package_data.notes
            )
            db.add(db_booking_package)
    
    # Add addons to booking if provided
    if booking.addons:
        for addon_data in booking.addons:
            db_booking_addon = BookingAddon(
                booking_id=db_booking.id,
                service_name=addon_data.service_name,
                service_price=addon_data.service_price,
                quantity=addon_data.quantity
            )
            db.add(db_booking_addon)
    
    db.commit()
    db.refresh(db_booking)
    
    # Update villa availability
    for villa_data in booking.villas:
        current_date = booking.check_in
        while current_date < booking.check_out:
            # Check if availability record exists
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == villa_data.villa_id,
                VillaAvailability.date == current_date
            ).first()
            
            if availability:
                # Update existing record
                availability.is_available = False
                availability.blocked_reason = f"Booked (Booking Code: {booking_code})"
                availability.updated_by = current_user_id
                availability.updated_at = datetime.utcnow()
            else:
                # Create new record
                db_availability = VillaAvailability(
                    villa_id=villa_data.villa_id,
                    date=current_date,
                    is_available=False,
                    blocked_reason=f"Booked (Booking Code: {booking_code})",
                    updated_by=current_user_id,
                    updated_at=datetime.utcnow()
                )
                db.add(db_availability)
            
            current_date += timedelta(days=1)
    
    db.commit()
    
    return db_booking


def update_booking(db: Session, booking_id: int, booking_update: BookingUpdate) -> Booking:
    """
    Update a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        booking_update: Booking update data
        
    Returns:
        Booking: Updated booking
        
    Raises:
        HTTPException: If booking not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Update booking fields
    update_data = booking_update.dict(exclude_unset=True)
    
    # Check if dates are being updated
    if "check_in" in update_data or "check_out" in update_data:
        check_in = update_data.get("check_in", db_booking.check_in)
        check_out = update_data.get("check_out", db_booking.check_out)
        
        # Check availability for all villas
        for booking_villa in db_booking.villas:
            is_available, _ = check_villa_availability(
                db, booking_villa.villa_id, check_in, check_out
            )
            
            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Villa with ID {booking_villa.villa_id} is not available for the updated dates"
                )
    
    for key, value in update_data.items():
        setattr(db_booking, key, value)
    
    db_booking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_booking)
    
    return db_booking


def update_booking_status(db: Session, booking_id: int, status_update: BookingStatusUpdate) -> Booking:
    """
    Update a booking status
    
    Args:
        db: Database session
        booking_id: Booking ID
        status_update: Booking status update data
        
    Returns:
        Booking: Updated booking
        
    Raises:
        HTTPException: If booking not found or invalid status
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Validate status
    valid_statuses = ["pending", "confirmed", "ongoing", "completed", "cancelled"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    db_booking.status = status_update.status
    db_booking.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_booking)
    
    return db_booking


def delete_booking(db: Session, booking_id: int) -> bool:
    """
    Delete a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        
    Returns:
        bool: True if booking was deleted
        
    Raises:
        HTTPException: If booking not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Free up villa availability
    for booking_villa in db_booking.villas:
        current_date = db_booking.check_in
        while current_date < db_booking.check_out:
            # Find availability record
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == booking_villa.villa_id,
                VillaAvailability.date == current_date
            ).first()
            
            if availability:
                # If the reason is for this booking, make it available again
                if availability.blocked_reason and f"Booking Code: {db_booking.booking_code}" in availability.blocked_reason:
                    availability.is_available = True
                    availability.blocked_reason = None
                    availability.updated_at = datetime.utcnow()
            
            current_date += timedelta(days=1)
    
    db.delete(db_booking)
    db.commit()
    
    return True


def add_booking_villa(db: Session, booking_id: int, villa_data: BookingVillaCreate) -> BookingVilla:
    """
    Add a villa to a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        villa_data: Villa data
        
    Returns:
        BookingVilla: Created booking villa
        
    Raises:
        HTTPException: If booking or villa not found, or villa not available
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    villa = get_villa(db, villa_data.villa_id)
    if not villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Villa with ID {villa_data.villa_id} not found"
        )
    
    # Check availability
    is_available, _ = check_villa_availability(
        db, villa_data.villa_id, db_booking.check_in, db_booking.check_out
    )
    
    if not is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Villa with ID {villa_data.villa_id} is not available for the booking dates"
        )
    
    # Add villa to booking
    db_booking_villa = BookingVilla(
        booking_id=booking_id,
        villa_id=villa_data.villa_id,
        assigned_at=datetime.utcnow()
    )
    
    db.add(db_booking_villa)
    db.commit()
    db.refresh(db_booking_villa)
    
    # Update villa availability
    current_date = db_booking.check_in
    while current_date < db_booking.check_out:
        # Check if availability record exists
        availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == villa_data.villa_id,
            VillaAvailability.date == current_date
        ).first()
        
        if availability:
            # Update existing record
            availability.is_available = False
            availability.blocked_reason = f"Booked (Booking Code: {db_booking.booking_code})"
            availability.updated_at = datetime.utcnow()
        else:
            # Create new record
            db_availability = VillaAvailability(
                villa_id=villa_data.villa_id,
                date=current_date,
                is_available=False,
                blocked_reason=f"Booked (Booking Code: {db_booking.booking_code})",
                updated_at=datetime.utcnow()
            )
            db.add(db_availability)
        
        current_date += timedelta(days=1)
    
    db.commit()
    
    return db_booking_villa


def remove_booking_villa(db: Session, booking_id: int, villa_id: int) -> bool:
    """
    Remove a villa from a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        villa_id: Villa ID
        
    Returns:
        bool: True if villa was removed
        
    Raises:
        HTTPException: If booking or booking villa not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    db_booking_villa = db.query(BookingVilla).filter(
        BookingVilla.booking_id == booking_id,
        BookingVilla.villa_id == villa_id
    ).first()
    
    if not db_booking_villa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Villa not found in booking"
        )
    
    # Free up villa availability
    current_date = db_booking.check_in
    while current_date < db_booking.check_out:
        # Find availability record
        availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == villa_id,
            VillaAvailability.date == current_date
        ).first()
        
        if availability:
            # If the reason is for this booking, make it available again
            if availability.blocked_reason and f"Booking Code: {db_booking.booking_code}" in availability.blocked_reason:
                availability.is_available = True
                availability.blocked_reason = None
                availability.updated_at = datetime.utcnow()
        
        current_date += timedelta(days=1)
    
    db.delete(db_booking_villa)
    db.commit()
    
    return True


def add_booking_package(db: Session, booking_id: int, package_data: BookingPackageCreate) -> BookingPackage:
    """
    Add a package to a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        package_data: Package data
        
    Returns:
        BookingPackage: Created booking package
        
    Raises:
        HTTPException: If booking not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Add package to booking
    db_booking_package = BookingPackage(
        booking_id=booking_id,
        package_name=package_data.package_name,
        package_price=package_data.package_price,
        notes=package_data.notes
    )
    
    db.add(db_booking_package)
    db.commit()
    db.refresh(db_booking_package)
    
    return db_booking_package


def remove_booking_package(db: Session, booking_id: int, package_id: int) -> bool:
    """
    Remove a package from a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        package_id: Package ID
        
    Returns:
        bool: True if package was removed
        
    Raises:
        HTTPException: If booking or booking package not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    db_booking_package = db.query(BookingPackage).filter(
        BookingPackage.booking_id == booking_id,
        BookingPackage.id == package_id
    ).first()
    
    if not db_booking_package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found in booking"
        )
    
    db.delete(db_booking_package)
    db.commit()
    
    return True


def add_booking_addon(db: Session, booking_id: int, addon_data: BookingAddonCreate) -> BookingAddon:
    """
    Add an addon to a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        addon_data: Addon data
        
    Returns:
        BookingAddon: Created booking addon
        
    Raises:
        HTTPException: If booking not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Add addon to booking
    db_booking_addon = BookingAddon(
        booking_id=booking_id,
        service_name=addon_data.service_name,
        service_price=addon_data.service_price,
        quantity=addon_data.quantity
    )
    
    db.add(db_booking_addon)
    db.commit()
    db.refresh(db_booking_addon)
    
    return db_booking_addon


def remove_booking_addon(db: Session, booking_id: int, addon_id: int) -> bool:
    """
    Remove an addon from a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        addon_id: Addon ID
        
    Returns:
        bool: True if addon was removed
        
    Raises:
        HTTPException: If booking or booking addon not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    db_booking_addon = db.query(BookingAddon).filter(
        BookingAddon.booking_id == booking_id,
        BookingAddon.id == addon_id
    ).first()
    
    if not db_booking_addon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Addon not found in booking"
        )
    
    db.delete(db_booking_addon)
    db.commit()
    
    return True


def get_booking_details(db: Session, booking_id: int) -> Dict[str, Any]:
    """
    Get booking details with financial information
    
    Args:
        db: Database session
        booking_id: Booking ID
        
    Returns:
        Dict[str, Any]: Booking details
        
    Raises:
        HTTPException: If booking not found
    """
    db_booking = get_booking(db, booking_id)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Calculate total price
    total_price = Decimal('0.00')
    
    # Villa prices
    nights = calculate_nights(db_booking.check_in, db_booking.check_out)
    for booking_villa in db_booking.villas:
        villa = db.query(Villa).filter(Villa.id == booking_villa.villa_id).first()
        if villa:
            total_price += villa.base_price * nights
    
    # Package prices
    for package in db_booking.packages:
        total_price += package.package_price
    
    # Addon prices
    for addon in db_booking.addons:
        total_price += addon.service_price * addon.quantity
    
    # Calculate total paid
    total_paid = db.query(func.sum(Payment.amount)).filter(
        Payment.booking_id == booking_id,
        Payment.status == "paid"
    ).scalar() or Decimal('0.00')
    
    # Calculate balance
    balance = total_price - total_paid
    
    # Create result
    result = {
        "booking": db_booking,
        "total_price": total_price,
        "total_paid": total_paid,
        "balance": balance
    }
    
    return result