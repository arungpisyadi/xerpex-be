"""
Booking services for the XerpeX ERP System
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
import logging

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking, BookingItem, BookingVilla, BookingHistory
from app.models.payment import Payment
from app.models.villa import Villa, VillaAvailability
from app.models.customer import Customer
from app.models.package import Package
from app.models.user import User
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingStatusUpdate,
    BookingItemCreate, BookingItemUpdate,
    BookingVillaCreate, BookingStatus
)
from app.services.customer import get_customer
from app.services.package import get_package
from app.services.villa import get_villa
from app.utils.helpers import generate_booking_code, calculate_nights
from app.utils.security import get_user_filter_condition, should_apply_user_isolation

# Set up logging
logger = logging.getLogger(__name__)


# ============================================================================
# Core READ Operations
# ============================================================================

def get_booking(db: Session, booking_id: int, current_user: User) -> Optional[Booking]:
    """
    Get a booking by ID with role-based user isolation
    
    Args:
        db: Database session
        booking_id: Booking ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Booking or None
        
    Raises:
        HTTPException: If booking not found or access denied
    """
    try:
        query = db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.items).joinedload(BookingItem.package),
            joinedload(Booking.villas).joinedload(BookingVilla.villa),
            joinedload(Booking.history).load_only(
                BookingHistory.id,
                BookingHistory.booking_id,
                BookingHistory.user_id,
                BookingHistory.field_name,
                BookingHistory.old_value,
                BookingHistory.new_value,
                BookingHistory.change_type,
                BookingHistory.payment_id,
                BookingHistory.created_at
            )
        ).filter(Booking.id == booking_id)
        
        # Apply user isolation based on role
        user_filter = get_user_filter_condition(current_user, Booking.user_id)
        if user_filter is not True:  # True means no filter (admin/finance)
            query = query.filter(user_filter)
        
        return query.first()
    except Exception as e:
        logger.error(f"Error getting booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving booking: {str(e)}"
        )


def get_booking_by_code(db: Session, booking_code: str, current_user: User) -> Optional[Booking]:
    """
    Get a booking by code with role-based user isolation
    
    Args:
        db: Database session
        booking_code: Booking code
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Booking or None
    """
    try:
        query = db.query(Booking).options(
            joinedload(Booking.customer),
            joinedload(Booking.items).joinedload(BookingItem.package),
            joinedload(Booking.villas).joinedload(BookingVilla.villa)
        ).filter(Booking.booking_code == booking_code)
        
        # Apply user isolation based on role
        user_filter = get_user_filter_condition(current_user, Booking.user_id)
        if user_filter is not True:
            query = query.filter(user_filter)
        
        return query.first()
    except Exception as e:
        logger.error(f"Error getting booking by code {booking_code}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving booking: {str(e)}"
        )


def get_bookings(
    db: Session, 
    current_user: User,
    skip: int = 0, 
    limit: int = 100,
    status: Optional[BookingStatus] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    check_in_from: Optional[date] = None,
    check_in_to: Optional[date] = None,
    villa_id: Optional[int] = None
) -> List[Booking]:
    """
    Get bookings with optional filtering and search (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        customer_id: Filter by customer ID
        search: Search by booking code or customer name
        check_in_from: Filter by check-in date from
        check_in_to: Filter by check-in date to
        villa_id: Filter by villa ID
        
    Returns:
        List[Booking]: List of bookings
    """
    try:
        query = db.query(Booking).options(
            joinedload(Booking.customer)
        )
        
        # Apply user isolation based on role
        user_filter = get_user_filter_condition(current_user, Booking.user_id)
        if user_filter is not True:  # True means no filter (admin/finance)
            query = query.filter(user_filter)
        
        # Apply filters
        if status:
            query = query.filter(Booking.status == status)
        
        if customer_id:
            query = query.filter(Booking.customer_id == customer_id)
        
        if search:
            query = query.join(Customer).filter(
                or_(
                    Booking.booking_code.ilike(f"%{search}%"),
                    Customer.name.ilike(f"%{search}%")
                )
            )
        
        if check_in_from:
            query = query.filter(Booking.check_in >= check_in_from)
        
        if check_in_to:
            query = query.filter(Booking.check_in <= check_in_to)
        
        if villa_id:
            query = query.join(BookingVilla).filter(BookingVilla.villa_id == villa_id)
        
        return query.order_by(Booking.created_at.desc()).offset(skip).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting bookings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving bookings: {str(e)}"
        )


# ============================================================================
# Core CREATE Operations
# ============================================================================

def create_booking(db: Session, booking: BookingCreate, current_user: User) -> Booking:
    """
    Create a new booking with items and villas
    
    Args:
        db: Database session
        booking: Booking data
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Created booking
        
    Raises:
        HTTPException: If validation fails
    """
    try:
        # Validate customer exists and is accessible
        customer = get_customer(db, booking.customer_id, current_user)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Validate sales_person_id if provided
        if booking.sales_person_id:
            sales_person = db.query(User).filter(User.id == booking.sales_person_id).first()
            if not sales_person:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sales person not found"
                )
        
        # Check if villas exist and are available
        for villa_id in booking.villas:
            villa = get_villa(db, villa_id)
            if not villa:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Villa with ID {villa_id} not found"
                )
            
            # Check availability
            is_available, unavailable_dates = check_villa_availability(
                db, villa_id, booking.check_in, booking.check_out
            )
            
            if not is_available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Villa with ID {villa_id} is not available for the selected dates"
                )
        
        # Generate unique booking code
        booking_code = generate_booking_code()
        while db.query(Booking).filter(Booking.booking_code == booking_code).first():
            booking_code = generate_booking_code()
        
        # Create booking
        db_booking = Booking(
            user_id=current_user.id,
            customer_id=booking.customer_id,
            sales_person_id=booking.sales_person_id,
            booking_code=booking_code,
            check_in=booking.check_in,
            check_out=booking.check_out,
            total_pax=booking.total_pax,
            status=booking.status,
            notes=booking.notes,
            total=Decimal('0.00'),
            tax_total=Decimal('0.00'),
            amount_paid=Decimal('0.00'),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(db_booking)
        db.flush()  # Get the booking ID
        
        # Add booking items
        items_total = Decimal('0.00')
        for item_data in booking.items:
            # Validate package exists
            package = get_package(db, item_data.package_id)
            if not package:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {item_data.package_id} not found"
                )
            
            # Check package access based on user role
            if should_apply_user_isolation(current_user) and package.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {item_data.package_id} not found"
                )
            
            booking_item = BookingItem(
                booking_id=db_booking.id,
                package_id=item_data.package_id,
                unit_price=item_data.unit_price,
                discount=item_data.discount,
                pax=item_data.pax,
                line_total=item_data.line_total,
                created_at=datetime.utcnow()
            )
            
            db.add(booking_item)
            items_total += item_data.line_total
        
        # Add villas to booking (simple junction table)
        villas_total = Decimal('0.00')
        for villa_id in booking.villas:
            villa = get_villa(db, villa_id)
            nights = calculate_nights(booking.check_in, booking.check_out)
            villa_total = villa.base_price * nights
            
            booking_villa = BookingVilla(
                booking_id=db_booking.id,
                villa_id=villa_id
            )
            
            db.add(booking_villa)
            villas_total += villa_total
            
            # Update villa availability
            update_villa_availability(
                db, villa_id, booking.check_in, booking.check_out,
                booking_code, current_user.id, is_available=False
            )
        
        # Update booking totals (amount_due will be automatically calculated as total - amount_paid)
        db_booking.total = items_total + villas_total
        
        # Create initial history record
        safe_log_booking_history(
            db, db_booking.id, current_user.id,
            field_name='status',
            old_value=None,
            new_value=booking.status,
            change_type='created'
        )
        
        db.commit()
        db.refresh(db_booking)
        
        logger.info(f"Created booking {booking_code} by user {current_user.id}")
        return db_booking
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating booking: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating booking: {str(e)}"
        )


# ============================================================================
# Core UPDATE Operations
# ============================================================================

def update_booking(
    db: Session, 
    booking_id: int, 
    booking_update: BookingUpdate, 
    current_user: User
) -> Booking:
    """
    Update a booking with business rules
    
    Args:
        db: Database session
        booking_id: Booking ID
        booking_update: Booking update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Updated booking
        
    Raises:
        HTTPException: If booking not found or validation fails
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        # Update booking fields and track changes
        update_data = booking_update.dict(exclude_unset=True, exclude={'items'})
        
        # Validate customer if being updated
        if 'customer_id' in update_data:
            customer = get_customer(db, update_data['customer_id'], current_user)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )
        
        # Validate sales_person_id if being updated
        if 'sales_person_id' in update_data and update_data['sales_person_id'] is not None:
            sales_person = db.query(User).filter(User.id == update_data['sales_person_id']).first()
            if not sales_person:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sales person not found"
                )
        
        # Check if dates are being updated
        if "check_in" in update_data or "check_out" in update_data:
            check_in = update_data.get("check_in", db_booking.check_in)
            check_out = update_data.get("check_out", db_booking.check_out)
            
            # Check availability for all villas
            for booking_villa in db_booking.villas:
                is_available, _ = check_villa_availability(
                    db, booking_villa.villa_id, check_in, check_out,
                    exclude_booking_id=booking_id
                )
                
                if not is_available:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Villa with ID {booking_villa.villa_id} is not available for the updated dates"
                    )
        
        # Track field changes for history
        for key, value in update_data.items():
            old_value = getattr(db_booking, key)
            if old_value != value:
                safe_log_booking_history(
                    db, booking_id, current_user.id,
                    field_name=key,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(value) if value is not None else None,
                    change_type='field_update'
                )
            setattr(db_booking, key, value)
        
        # Update items if provided
        if booking_update.items is not None:
            # Delete existing items
            db.query(BookingItem).filter(BookingItem.booking_id == booking_id).delete()
            
            # Add new items
            items_total = Decimal('0.00')
            for item_data in booking_update.items:
                # Validate package
                package = get_package(db, item_data.package_id)
                if not package:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Package with ID {item_data.package_id} not found"
                    )
                
                if should_apply_user_isolation(current_user) and package.user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Package with ID {item_data.package_id} not found"
                    )
                
                booking_item = BookingItem(
                    booking_id=db_booking.id,
                    package_id=item_data.package_id,
                    unit_price=item_data.unit_price,
                    discount=item_data.discount,
                    pax=item_data.pax,
                    line_total=item_data.line_total,
                    created_at=datetime.utcnow()
                )
                
                db.add(booking_item)
                items_total += item_data.line_total
            
            # Recalculate totals
            recalculate_booking_totals(db, booking_id, current_user)
        
        db_booking.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_booking)
        
        logger.info(f"Updated booking {booking_id} by user {current_user.id}")
        return db_booking
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating booking: {str(e)}"
        )


def update_booking_status(
    db: Session, 
    booking_id: int, 
    status_update: BookingStatusUpdate, 
    current_user: User
) -> Booking:
    """
    Update booking status with workflow validation
    
    Args:
        db: Database session
        booking_id: Booking ID
        status_update: Status update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Updated booking
        
    Raises:
        HTTPException: If booking not found or invalid status transition
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Validate status transitions
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['checked_in', 'cancelled'],
            'checked_in': ['checked_out', 'cancelled'],
            'checked_out': ['completed'],
            'completed': [],  # Terminal state
            'cancelled': []  # Terminal state
        }
        
        if status_update.status not in valid_transitions.get(db_booking.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot change status from '{db_booking.status}' to '{status_update.status}'"
            )
        
        # Create history record
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='status',
            old_value=db_booking.status,
            new_value=status_update.status,
            change_type='status_change'
        )
        
        db_booking.status = status_update.status
        db_booking.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_booking)
        
        logger.info(f"Updated booking {booking_id} status to {status_update.status} by user {current_user.id}")
        return db_booking
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating booking status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating booking status: {str(e)}"
        )


# ============================================================================
# Core DELETE Operations
# ============================================================================

def delete_booking(db: Session, booking_id: int, current_user: User) -> bool:
    """
    Delete a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if booking was deleted
        
    Raises:
        HTTPException: If booking not found or cannot be deleted
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Only allow deletion of pending or cancelled bookings
        if db_booking.status not in ['pending', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending or cancelled bookings can be deleted"
            )
        
        # Free up villa availability
        for booking_villa in db_booking.villas:
            update_villa_availability(
                db, booking_villa.villa_id, 
                db_booking.check_in, db_booking.check_out,
                db_booking.booking_code, current_user.id, 
                is_available=True
            )
        
        # Log history event before deletion
        safe_log_booking_history(
            db=db,
            booking_id=db_booking.id,
            user_id=current_user.id,
            change_type="deleted",
            field_name="status",
            old_value=db_booking.status,
            new_value=None
        )
        
        db.delete(db_booking)
        db.commit()
        
        logger.info(f"Deleted booking {booking_id} by user {current_user.id}")
        return True
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting booking: {str(e)}"
        )


# ============================================================================
# Booking ITEM Operations
# ============================================================================

def add_booking_item(
    db: Session, 
    booking_id: int, 
    item: BookingItemCreate, 
    current_user: User
) -> BookingItem:
    """
    Add item to booking and recalculate totals
    
    Args:
        db: Database session
        booking_id: Booking ID
        item: Item data
        current_user: Current user (for role-based access control)
        
    Returns:
        BookingItem: Created booking item
        
    Raises:
        HTTPException: If booking or package not found
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        # Validate package
        package = get_package(db, item.package_id)
        if not package:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with ID {item.package_id} not found"
            )
        
        if should_apply_user_isolation(current_user) and package.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with ID {item.package_id} not found"
            )
        
        # Create booking item
        booking_item = BookingItem(
            booking_id=booking_id,
            package_id=item.package_id,
            unit_price=item.unit_price,
            discount=item.discount,
            pax=item.pax,
            line_total=item.line_total,
            created_at=datetime.utcnow()
        )
        
        db.add(booking_item)
        
        # Create history record
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='items',
            old_value=None,
            new_value=f"Added item: {package.name}",
            change_type='item_added'
        )
        
        # Recalculate totals
        recalculate_booking_totals(db, booking_id, current_user)
        
        db.commit()
        db.refresh(booking_item)
        
        logger.info(f"Added item to booking {booking_id} by user {current_user.id}")
        return booking_item
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding item to booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding item: {str(e)}"
        )


def update_booking_item(
    db: Session, 
    booking_id: int, 
    item_id: int, 
    item_update: BookingItemUpdate, 
    current_user: User
) -> BookingItem:
    """
    Update booking item and recalculate totals
    
    Args:
        db: Database session
        booking_id: Booking ID
        item_id: Item ID
        item_update: Item update data
        current_user: Current user (for role-based access control)
        
    Returns:
        BookingItem: Updated booking item
        
    Raises:
        HTTPException: If booking or item not found
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        booking_item = db.query(BookingItem).filter(
            BookingItem.booking_id == booking_id,
            BookingItem.id == item_id
        ).first()
        
        if not booking_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking item not found"
            )
        
        # Update item fields
        update_data = item_update.dict(exclude_unset=True)
        
        # Validate package if being updated
        if 'package_id' in update_data:
            package = get_package(db, update_data['package_id'])
            if not package:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {update_data['package_id']} not found"
                )
            
            if should_apply_user_isolation(current_user) and package.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {update_data['package_id']} not found"
                )
        
        for key, value in update_data.items():
            setattr(booking_item, key, value)
        
        # Create history record
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='items',
            old_value=None,
            new_value=f"Updated item {item_id}",
            change_type='field_update'
        )
        
        # Recalculate totals
        recalculate_booking_totals(db, booking_id, current_user)
        
        db.commit()
        db.refresh(booking_item)
        
        logger.info(f"Updated item {item_id} in booking {booking_id} by user {current_user.id}")
        return booking_item
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating item {item_id} in booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating item: {str(e)}"
        )


def remove_booking_item(
    db: Session, 
    booking_id: int, 
    item_id: int, 
    current_user: User
) -> bool:
    """
    Remove item from booking and recalculate totals
    
    Args:
        db: Database session
        booking_id: Booking ID
        item_id: Item ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if item was removed
        
    Raises:
        HTTPException: If booking or item not found
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        booking_item = db.query(BookingItem).filter(
            BookingItem.booking_id == booking_id,
            BookingItem.id == item_id
        ).first()
        
        if not booking_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking item not found"
            )
        
        # Create history record
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='items',
            old_value=f"Item {item_id}",
            new_value=None,
            change_type='item_removed'
        )
        
        db.delete(booking_item)
        
        # Recalculate totals
        recalculate_booking_totals(db, booking_id, current_user)
        
        db.commit()
        
        logger.info(f"Removed item {item_id} from booking {booking_id} by user {current_user.id}")
        return True
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing item {item_id} from booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing item: {str(e)}"
        )


# ============================================================================
# Booking VILLA Operations
# ============================================================================

def add_booking_villa(
    db: Session, 
    booking_id: int, 
    villa: BookingVillaCreate, 
    current_user: User
) -> BookingVilla:
    """
    Add villa to booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        villa: Villa data
        current_user: Current user (for role-based access control)
        
    Returns:
        BookingVilla: Created booking villa
        
    Raises:
        HTTPException: If booking or villa not found, or villa not available
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        villa_obj = get_villa(db, villa.villa_id)
        if not villa_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Villa with ID {villa.villa_id} not found"
            )
        
        # Check availability
        is_available, _ = check_villa_availability(
            db, villa.villa_id, db_booking.check_in, db_booking.check_out
        )
        
        if not is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Villa with ID {villa.villa_id} is not available for the booking dates"
            )
        
        # Add villa to booking (simple junction table)
        booking_villa = BookingVilla(
            booking_id=booking_id,
            villa_id=villa.villa_id
        )
        
        db.add(booking_villa)
        
        # Update villa availability
        update_villa_availability(
            db, villa.villa_id, db_booking.check_in, db_booking.check_out,
            db_booking.booking_code, current_user.id, is_available=False
        )
        
        # Create history record
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='villas',
            old_value=None,
            new_value=f"Added villa: {villa_obj.name}",
            change_type='villa_added'
        )
        
        # Recalculate totals
        recalculate_booking_totals(db, booking_id, current_user)
        
        db.commit()
        db.refresh(booking_villa)
        
        logger.info(f"Added villa {villa.villa_id} to booking {booking_id} by user {current_user.id}")
        return booking_villa
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding villa to booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding villa: {str(e)}"
        )


def update_booking_villa(
    db: Session,
    booking_id: int,
    villa_id: int,
    villa_update: Dict[str, Any],
    current_user: User
) -> BookingVilla:
    """
    Update booking villa (simplified - junction table has no editable fields)
    
    Note: Since booking_villas is now a simple junction table, this function
    is kept for API compatibility but has no fields to update.
    
    Args:
        db: Database session
        booking_id: Booking ID
        villa_id: Villa ID
        villa_update: Villa update data (ignored)
        current_user: Current user (for role-based access control)
        
    Returns:
        BookingVilla: Booking villa record
        
    Raises:
        HTTPException: If booking or villa not found
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        booking_villa = db.query(BookingVilla).filter(
            BookingVilla.booking_id == booking_id,
            BookingVilla.villa_id == villa_id
        ).first()
        
        if not booking_villa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Villa not found in booking"
            )
        
        # No fields to update in simple junction table
        logger.info(f"Booking villa {villa_id} in booking {booking_id} - no updates needed (junction table)")
        return booking_villa
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing villa {villa_id} in booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing villa: {str(e)}"
        )


def remove_booking_villa(
    db: Session, 
    booking_id: int, 
    villa_id: int, 
    current_user: User
) -> bool:
    """
    Remove villa from booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        villa_id: Villa ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if villa was removed
        
    Raises:
        HTTPException: If booking or villa not found
    """
    try:
        db_booking = get_booking(db, booking_id, current_user)
        if not db_booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check if booking can be modified
        if db_booking.status in ['completed', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify booking with status '{db_booking.status}'"
            )
        
        booking_villa = db.query(BookingVilla).filter(
            BookingVilla.booking_id == booking_id,
            BookingVilla.villa_id == villa_id
        ).first()
        
        if not booking_villa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Villa not found in booking"
            )
        
        # Free up villa availability
        update_villa_availability(
            db, villa_id, db_booking.check_in, db_booking.check_out,
            db_booking.booking_code, current_user.id, is_available=True
        )
        
        # Create history record
        villa_obj = get_villa(db, villa_id)
        safe_log_booking_history(
            db, booking_id, current_user.id,
            field_name='villas',
            old_value=f"Villa: {villa_obj.name if villa_obj else villa_id}",
            new_value=None,
            change_type='villa_removed'
        )
        
        db.delete(booking_villa)
        
        # Recalculate totals
        recalculate_booking_totals(db, booking_id, current_user)
        
        db.commit()
        
        logger.info(f"Removed villa {villa_id} from booking {booking_id} by user {current_user.id}")
        return True
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing villa {villa_id} from booking {booking_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing villa: {str(e)}"
        )


# ============================================================================
# Calculation Operations
# ============================================================================

def calculate_booking_totals(
    items: List[BookingItem],
    villas: List[BookingVilla],
    check_in: date,
    check_out: date
) -> Dict[str, Decimal]:
    """
    Calculate booking totals
    
    Args:
        items: List of booking items
        villas: List of booking villas
        check_in: Booking check-in date
        check_out: Booking check-out date
        
    Returns:
        Dict: Dictionary with subtotal, tax_total, and total
    """
    items_subtotal = sum(item.line_total for item in items)
    
    # Calculate villa subtotal from booking dates and villa base prices
    nights = calculate_nights(check_in, check_out)
    villas_subtotal = Decimal('0.00')
    for booking_villa in villas:
        if booking_villa.villa and booking_villa.villa.base_price:
            villas_subtotal += booking_villa.villa.base_price * nights
    
    subtotal = items_subtotal + villas_subtotal
    
    return {
        'subtotal': subtotal,
        'items_subtotal': items_subtotal,
        'villas_subtotal': villas_subtotal,
        'tax_total': Decimal('0.00'),
        'total': subtotal
    }


def recalculate_booking_totals(
    db: Session, 
    booking_id: int, 
    current_user: User
) -> Booking:
    """
    Recalculate and update booking totals
    
    Args:
        db: Database session
        booking_id: Booking ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Booking: Updated booking
    """
    db_booking = get_booking(db, booking_id, current_user)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Calculate totals
    totals = calculate_booking_totals(
        db_booking.items,
        db_booking.villas,
        db_booking.check_in,
        db_booking.check_out
    )
    
    # Update booking
    db_booking.total = totals['total']
    db_booking.tax_total = totals['tax_total']
    db_booking.amount_due = totals['total'] - db_booking.amount_paid
    db_booking.updated_at = datetime.utcnow()
    
    return db_booking


# ============================================================================
# History Operations
# ============================================================================

def create_booking_history(
    db: Session,
    booking_id: int,
    user_id: int,
    field_name: str,
    old_value: Optional[str],
    new_value: Optional[str],
    change_type: str
) -> BookingHistory:
    """
    Create booking history record
    
    Args:
        db: Database session
        booking_id: Booking ID
        user_id: User ID who made the change
        field_name: Name of the field changed
        old_value: Old value
        new_value: New value
        change_type: Type of change
        
    Returns:
        BookingHistory: Created history record
    """
    history = BookingHistory(
        booking_id=booking_id,
        user_id=user_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        change_type=change_type,
        created_at=datetime.utcnow()
    )
    
    db.add(history)


def log_booking_history(
    db: Session,
    booking_id: int,
    user_id: Optional[int],
    change_type: str,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    payment_id: Optional[int] = None
) -> BookingHistory:
    """Log a booking history event."""
    history_entry = BookingHistory(
        booking_id=booking_id,
        user_id=user_id,
        change_type=change_type,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value,
        payment_id=payment_id
    )
    db.add(history_entry)
    db.commit()
    return history_entry


def safe_log_booking_history(
    db: Session,
    booking_id: int,
    user_id: Optional[int],
    change_type: str,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    payment_id: Optional[int] = None
) -> Optional[BookingHistory]:
    """Safely log booking history without affecting main operations."""
    try:
        return log_booking_history(
            db=db,
            booking_id=booking_id,
            user_id=user_id,
            change_type=change_type,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            payment_id=payment_id
        )
    except Exception as e:
        print(f"Failed to log booking history: {e}")
        db.rollback()
        return None
    return history


def get_booking_history(
    db: Session, 
    booking_id: int, 
    current_user: User
) -> List[BookingHistory]:
    """
    Get booking history with user details
    
    Args:
        db: Database session
        booking_id: Booking ID
        current_user: Current user (for role-based access control)
        
    Returns:
        List[BookingHistory]: List of history records
    """
    # Check booking access
    db_booking = get_booking(db, booking_id, current_user)
    if not db_booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    return db.query(BookingHistory).filter(
        BookingHistory.booking_id == booking_id
    ).order_by(BookingHistory.created_at.desc()).all()


# ============================================================================
# Villa Availability Operations
# ============================================================================

def check_villa_availability(
    db: Session,
    villa_id: int,
    check_in: date,
    check_out: date,
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, List[date]]:
    """
    Check if a villa is available for the given dates
    
    Args:
        db: Database session
        villa_id: Villa ID
        check_in: Check-in date
        check_out: Check-out date
        exclude_booking_id: Booking ID to exclude from check
        
    Returns:
        Tuple[bool, List[date]]: (is_available, list of unavailable dates)
    """
    unavailable_dates = []
    current_date = check_in
    
    while current_date < check_out:
        # Check if date is blocked in villa_availability
        availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == villa_id,
            VillaAvailability.date == current_date,
            VillaAvailability.is_available == False
        ).first()
        
        if availability:
            # Check if it's blocked by the excluded booking
            if exclude_booking_id:
                booking = db.query(Booking).filter(
                    Booking.id == exclude_booking_id
                ).first()
                if booking and f"Booking Code: {booking.booking_code}" in availability.blocked_reason:
                    # This is the same booking, skip
                    current_date += timedelta(days=1)
                    continue
            
            unavailable_dates.append(current_date)
        
        current_date += timedelta(days=1)
    
    is_available = len(unavailable_dates) == 0
    return is_available, unavailable_dates


def update_villa_availability(
    db: Session,
    villa_id: int,
    check_in: date,
    check_out: date,
    booking_code: str,
    user_id: int,
    is_available: bool = False
) -> None:
    """
    Update villa availability for date range
    
    Args:
        db: Database session
        villa_id: Villa ID
        check_in: Check-in date
        check_out: Check-out date
        booking_code: Booking code
        user_id: User ID
        is_available: Whether to mark as available or unavailable
    """
    current_date = check_in
    
    while current_date < check_out:
        # Check if availability record exists
        availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == villa_id,
            VillaAvailability.date == current_date
        ).first()
        
        if availability:
            # Update existing record
            availability.is_available = is_available
            if is_available:
                availability.blocked_reason = None
            else:
                availability.blocked_reason = f"Booked (Booking Code: {booking_code})"
            availability.updated_by = user_id
            availability.updated_at = datetime.utcnow()
        else:
            # Create new record
            db_availability = VillaAvailability(
                villa_id=villa_id,
                date=current_date,
                is_available=is_available,
                blocked_reason=None if is_available else f"Booked (Booking Code: {booking_code})",
                updated_by=user_id,
                updated_at=datetime.utcnow()
            )
            db.add(db_availability)
        
        current_date += timedelta(days=1)


# ============================================================================
# Statistics Operations
# ============================================================================

def get_booking_statistics(
    db: Session,
    current_user: User,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Get booking statistics for dashboard
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        from_date: Filter from date
        to_date: Filter to date
        
    Returns:
        Dict: Booking statistics
    """
    query = db.query(Booking)
    
    # Apply user isolation
    user_filter = get_user_filter_condition(current_user, Booking.user_id)
    if user_filter is not True:
        query = query.filter(user_filter)
    
    # Apply date filters
    if from_date:
        query = query.filter(Booking.check_in >= from_date)
    if to_date:
        query = query.filter(Booking.check_in <= to_date)
    
    # Count total bookings
    total_bookings = query.count()
    
    # Status breakdown
    status_counts = db.query(
        Booking.status,
        func.count(Booking.id).label('count')
    ).filter(user_filter if user_filter is not True else True).group_by(Booking.status).all()
    
    # Calculate total revenue
    total_revenue = query.with_entities(
        func.sum(Booking.total)
    ).scalar() or Decimal('0.00')
    
    # Calculate total paid
    total_paid = query.with_entities(
        func.sum(Booking.amount_paid)
    ).scalar() or Decimal('0.00')
    
    # Recent bookings
    recent_bookings = query.options(
        joinedload(Booking.customer)
    ).order_by(Booking.created_at.desc()).limit(5).all()
    
    return {
        'total_bookings': total_bookings,
        'status_breakdown': {status: count for status, count in status_counts},
        'total_revenue': total_revenue,
        'total_paid': total_paid,
        'outstanding': total_revenue - total_paid,
        'recent_bookings': recent_bookings
    }


# ============================================================================
# Validation Operations
# ============================================================================

def validate_booking_dates(
    db: Session,
    check_in: date,
    check_out: date,
    villa_ids: List[int],
    exclude_booking_id: Optional[int] = None
) -> Tuple[bool, List[str]]:
    """
    Validate booking dates and villa availability
    
    Args:
        db: Database session
        check_in: Check-in date
        check_out: Check-out date
        villa_ids: List of villa IDs
        exclude_booking_id: Booking ID to exclude from check
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, error_messages)
    """
    error_messages = []
    
    # Check if dates are valid
    if check_out <= check_in:
        error_messages.append("Check-out date must be after check-in date")
    
    # Check if check-in is in the past
    if check_in < date.today():
        error_messages.append("Check-in date cannot be in the past")
    
    # Check villa availability
    for villa_id in villa_ids:
        is_available, unavailable_dates = check_villa_availability(
            db, villa_id, check_in, check_out, exclude_booking_id
        )
        
        if not is_available:
            villa = get_villa(db, villa_id)
            villa_name = villa.name if villa else f"Villa {villa_id}"
            error_messages.append(
                f"{villa_name} is not available for dates: {', '.join(str(d) for d in unavailable_dates)}"
            )
    
    is_valid = len(error_messages) == 0
    return is_valid, error_messages