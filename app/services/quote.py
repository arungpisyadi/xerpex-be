"""
Quote services for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.quote import Quote, QuoteItem, QuoteVilla, QuoteHistory
from app.models.customer import Customer
from app.models.package import Package
from app.models.tax import Tax
from app.models.user import User
from app.models.villa import Villa
from app.schemas.quote import (
    QuoteCreate, QuoteUpdate, QuoteStatusUpdate, QuoteItemCreate,
    QuoteConversionRequest, QuoteStatus
)
from app.services.customer import get_customer
from app.services.package import get_package
from app.services.villa import get_villa
from app.services.tax import calculate_total_with_taxes
from app.utils.helpers import generate_quote_number
from app.utils.security import get_user_filter_condition, should_apply_user_isolation


def get_quote(db: Session, quote_id: int, current_user: User) -> Optional[Quote]:
    """
    Get a quote by ID with role-based user isolation
    
    Args:
        db: Database session
        quote_id: Quote ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Quote: Quote or None
    """
    query = db.query(Quote).options(
        joinedload(Quote.customer),
        joinedload(Quote.items).joinedload(QuoteItem.package),
        joinedload(Quote.villas).joinedload(QuoteVilla.villa),
        joinedload(Quote.history).load_only(
            QuoteHistory.id,
            QuoteHistory.quote_id,
            QuoteHistory.user_id,
            QuoteHistory.event_type,
            QuoteHistory.event_category,
            QuoteHistory.description,
            QuoteHistory.event_metadata,
            QuoteHistory.created_at
        )
    ).filter(Quote.id == quote_id)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Quote.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.first()


def get_quotes(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    status: Optional[QuoteStatus] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[Quote]:
    """
    Get quotes with optional filtering and search (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by quote status
        customer_id: Filter by customer ID
        search: Search by quote number or customer name
        from_date: Filter by issue date from
        to_date: Filter by issue date to
        
    Returns:
        List[Quote]: List of quotes
    """
    query = db.query(Quote).options(
        joinedload(Quote.customer),
        joinedload(Quote.villas).joinedload(QuoteVilla.villa)
    )
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Quote.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    # Apply filters
    if status:
        query = query.filter(Quote.status == status)
    
    if customer_id:
        query = query.filter(Quote.customer_id == customer_id)
    
    if search:
        query = query.join(Customer).filter(
            or_(
                Quote.quote_number.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%")
            )
        )
    
    if from_date:
        query = query.filter(Quote.issue_date >= from_date)
    
    if to_date:
        query = query.filter(Quote.issue_date <= to_date)
    
    return query.order_by(Quote.created_at.desc()).offset(skip).limit(limit).all()


def create_quote(db: Session, quote: QuoteCreate, current_user: User) -> Quote:
    """
    Create a new quote with items

    Args:
        db: Database session
        quote: Quote data
        current_user: Current user (for role-based access control)

    Returns:
        Quote: Created quote

    Raises:
        HTTPException: If customer not found or validation fails
    """
    # Validate customer exists and is accessible
    customer = get_customer(db, quote.customer_id, current_user)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Validate sales_person_id if provided
    if quote.sales_person_id:
        sales_person = db.query(User).filter(User.id == quote.sales_person_id).first()
        if not sales_person:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales person not found"
            )

    # Validate villas if provided (must happen before creating any records)
    for villa_id in quote.villas:
        villa = get_villa(db, villa_id)
        if not villa:
            # Raise ValueError for validation errors in service layer
            # Controllers can catch and convert to HTTPException if needed
            raise ValueError(f"Villa with ID {villa_id} not found")

    # Generate quote number
    quote_number = generate_quote_number()

    # Ensure quote number is unique
    while db.query(Quote).filter(Quote.quote_number == quote_number).first():
        quote_number = generate_quote_number()

    # Create quote
    db_quote = Quote(
        user_id=current_user.id,
        customer_id=quote.customer_id,
        sales_person_id=quote.sales_person_id,
        quote_number=quote_number,
        issue_date=quote.issue_date,
        expiry_date=quote.expiry_date,
        check_in=quote.check_in,
        check_out=quote.check_out,
        status=quote.status,
        notes=quote.notes,
        total=Decimal('0.00'),
        tax_total=Decimal('0.00'),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_quote)
    db.flush()  # Get the quote ID
    
    # Add quote items
    total_amount = Decimal('0.00')
    for item_data in quote.items:
        # Validate package exists and is accessible
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
        
        # Create quote item
        quote_item = QuoteItem(
            quote_id=db_quote.id,
            package_id=item_data.package_id,
            unit_price=item_data.unit_price,
            discount=item_data.discount,
            pax=item_data.pax,
            line_total=item_data.line_total,
            created_at=datetime.utcnow()
        )
        
        db.add(quote_item)
        total_amount += item_data.line_total
    
    # Create quote-villa relationships
    villas_total = Decimal('0.00')
    for villa_id in quote.villas:
        villa = get_villa(db, villa_id)
        villa_total = villa.base_price  # For quotes, just use base price without nights calculation
        
        quote_villa = QuoteVilla(
            quote_id=db_quote.id,
            villa_id=villa_id
        )
        db.add(quote_villa)
        villas_total += villa_total
    
    # Update quote totals
    db_quote.total = total_amount + villas_total
    db_quote.tax_total = Decimal('0.00')
    
    db.commit()
    db.refresh(db_quote)
    
    # Log history event
    safe_log_quote_history(
        db=db,
        quote_id=db_quote.id,
        user_id=current_user.id,
        event_type="quote_created",
        event_category="lifecycle",
        description="Quote created",
        metadata={
            "quote_number": db_quote.quote_number,
            "customer_name": customer.name,
            "total_amount": str(db_quote.total),
            "status": db_quote.status
        }
    )
    
    return db_quote


def update_quote(
    db: Session,
    quote_id: int,
    quote_update: QuoteUpdate,
    current_user: User
) -> Quote:
    """
    Update a quote
    
    Args:
        db: Database session
        quote_id: Quote ID
        quote_update: Quote update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Quote: Updated quote
        
    Raises:
        HTTPException: If quote not found or validation fails
    """
    db_quote = get_quote(db, quote_id, current_user)
    if not db_quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Check if quote can be modified
    if db_quote.status in ['accepted', 'declined', 'expired']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify quote with status '{db_quote.status}'"
        )
    
    # Update quote fields (exclude items and villas as they're handled separately)
    update_data = quote_update.dict(exclude_unset=True, exclude={'items', 'villas'})
    
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
    
    for key, value in update_data.items():
        setattr(db_quote, key, value)
    
    # Validate villas if provided in update (must happen before any changes)
    if quote_update.villas is not None:
        for villa_id in quote_update.villas:
            villa = get_villa(db, villa_id)
            if not villa:
                # Raise ValueError for validation errors in service layer
                raise ValueError(f"Villa with ID {villa_id} not found")
    
    # Update items if provided
    if quote_update.items is not None:
        # Delete existing items
        db.query(QuoteItem).filter(QuoteItem.quote_id == quote_id).delete()
        
        # Add new items
        total_amount = Decimal('0.00')
        for item_data in quote_update.items:
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
            
            quote_item = QuoteItem(
                quote_id=db_quote.id,
                package_id=item_data.package_id,
                unit_price=item_data.unit_price,
                discount=item_data.discount,
                pax=item_data.pax,
                line_total=item_data.line_total,
                created_at=datetime.utcnow()
            )
            
            db.add(quote_item)
            total_amount += item_data.line_total
        
        # Calculate villas total
        villas_total = Decimal('0.00')
        if quote_update.villas is not None:
            # If villas are being updated, delete existing and add new ones
            db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).delete()
            
            for villa_id in quote_update.villas:
                villa = get_villa(db, villa_id)
                villa_total = villa.base_price
                
                quote_villa = QuoteVilla(
                    quote_id=db_quote.id,
                    villa_id=villa_id
                )
                db.add(quote_villa)
                villas_total += villa_total
        else:
            # Recalculate existing villas total
            for quote_villa in db_quote.villas:
                if quote_villa.villa:
                    villas_total += quote_villa.villa.base_price
        
        # Update totals
        db_quote.total = total_amount + villas_total
    elif quote_update.villas is not None:
        # Only villas are being updated (items not provided)
        # Delete existing villas and add new ones
        db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).delete()
        
        villas_total = Decimal('0.00')
        for villa_id in quote_update.villas:
            villa = get_villa(db, villa_id)
            villa_total = villa.base_price
            
            quote_villa = QuoteVilla(
                quote_id=db_quote.id,
                villa_id=villa_id
            )
            db.add(quote_villa)
            villas_total += villa_total
        
        # Recalculate items total
        items_total = sum(item.line_total for item in db_quote.items)
        
        # Update total
        db_quote.total = items_total + villas_total
    
    db_quote.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_quote)
    
    # Log history event for update
    changed_fields = {}
    for key in update_data.keys():
        if key not in ['items', 'villas']:
            changed_fields[key] = str(update_data[key])
    
    safe_log_quote_history(
        db=db,
        quote_id=db_quote.id,
        user_id=current_user.id,
        event_type="quote_updated",
        event_category="data",
        description="Quote updated",
        metadata={
            "changed_fields": changed_fields,
            "items_updated": quote_update.items is not None,
            "villas_updated": quote_update.villas is not None,
            "new_total": str(db_quote.total)
        }
    )
    
    return db_quote


def update_quote_notes(
    db: Session,
    quote_id: int,
    notes: Optional[str],
    current_user: User
) -> Quote:
    """
    Update quote notes with proper access control and business rules
    
    Args:
        db: Database session
        quote_id: Quote ID
        notes: Notes value (None to clear notes)
        current_user: Current user (for role-based access control)
        
    Returns:
        Quote: Updated quote
        
    Raises:
        HTTPException: If quote not found or validation fails
    """
    # Get quote with proper access control
    db_quote = get_quote(db, quote_id, current_user)
    if not db_quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Check if quote can be modified (same business rules as update_quote)
    if db_quote.status in ['accepted', 'declined', 'expired']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify quote with status '{db_quote.status}'"
        )
    
    # Update notes field
    db_quote.notes = notes
    db_quote.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_quote)
    
    return db_quote


def update_quote_status(
    db: Session,
    quote_id: int,
    status_update: QuoteStatusUpdate,
    current_user: User
) -> Quote:
    """
    Update quote status with workflow validation
    
    Args:
        db: Database session
        quote_id: Quote ID
        status_update: Status update data
        current_user: Current user (for role-based access control)
        
    Returns:
        Quote: Updated quote
        
    Raises:
        HTTPException: If quote not found or invalid status transition
    """
    db_quote = get_quote(db, quote_id, current_user)
    if not db_quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Validate status transitions
    valid_transitions = {
        'draft': ['sent', 'declined'],
        'sent': ['accepted', 'declined', 'expired'],
        'accepted': [],  # Terminal state
        'declined': ['draft'],  # Can be reopened
        'expired': ['draft']  # Can be reopened
    }
    
    if status_update.status not in valid_transitions.get(db_quote.status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot change status from '{db_quote.status}' to '{status_update.status}'"
        )
    
    # Check expiry date for certain status changes
    if status_update.status == 'expired' and db_quote.expiry_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot mark quote as expired before expiry date"
        )
    
    old_status = db_quote.status
    db_quote.status = status_update.status
    db_quote.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_quote)
    
    # Log history event for status change
    safe_log_quote_history(
        db=db,
        quote_id=db_quote.id,
        user_id=current_user.id,
        event_type="status_changed",
        event_category="status",
        description=f"Quote status changed from '{old_status}' to '{status_update.status}'",
        metadata={
            "old_status": old_status,
            "new_status": status_update.status
        }
    )
    
    return db_quote


def delete_quote(db: Session, quote_id: int, current_user: User) -> bool:
    """
    Delete a quote
    
    Args:
        db: Database session
        quote_id: Quote ID
        current_user: Current user (for role-based access control)
        
    Returns:
        bool: True if quote was deleted
        
    Raises:
        HTTPException: If quote not found or cannot be deleted
    """
    db_quote = get_quote(db, quote_id, current_user)
    if not db_quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Only allow deletion of draft quotes
    if db_quote.status != 'draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft quotes can be deleted"
        )
    
    # Check if quote has been converted to invoice
    if db_quote.invoices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete quote that has been converted to invoice"
        )
    
    # Log history event before deletion
    safe_log_quote_history(
        db=db,
        quote_id=db_quote.id,
        user_id=current_user.id,
        event_type="quote_deleted",
        event_category="lifecycle",
        description="Quote deleted",
        metadata={
            "quote_number": db_quote.quote_number,
            "status": db_quote.status
        }
    )
    
    db.delete(db_quote)
    db.commit()
    
    return True


def calculate_quote_totals(
    db: Session, 
    items: List[QuoteItemCreate], 
    user_id: int,
    tax_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Calculate quote totals including taxes
    
    Args:
        db: Database session
        items: List of quote items
        user_id: Current user ID for isolation
        tax_ids: Optional list of tax IDs to apply
        
    Returns:
        Dict: Dictionary with subtotal, tax_total, and total
    """
    subtotal = sum(item.line_total for item in items)
    
    # Always return tax_total as 0 regardless of tax_ids
    # if tax_ids:
    #     taxes = db.query(Tax).filter(
    #         and_(Tax.id.in_(tax_ids), Tax.user_id == user_id)
    #     ).all()
    #
    #     return calculate_total_with_taxes(subtotal, taxes)
    
    return {
        'subtotal': subtotal,
        'tax_total': Decimal('0.00'),
        'total': subtotal,
        'tax_breakdown': []
    }


def get_quote_statistics(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get quote statistics for dashboard
    
    Args:
        db: Database session
        user_id: Current user ID for isolation
        
    Returns:
        Dict: Quote statistics
    """
    total_quotes = db.query(Quote).filter(Quote.user_id == user_id).count()
    
    status_counts = db.query(
        Quote.status,
        func.count(Quote.id).label('count')
    ).filter(Quote.user_id == user_id).group_by(Quote.status).all()
    
    # Calculate total value
    total_value = db.query(
        func.sum(Quote.total)
    ).filter(Quote.user_id == user_id).scalar() or Decimal('0.00')
    
    # Recent quotes
    recent_quotes = db.query(Quote).options(
        joinedload(Quote.customer)
    ).filter(Quote.user_id == user_id).order_by(
        Quote.created_at.desc()
    ).limit(5).all()
    
    return {
        'total_quotes': total_quotes,
        'status_breakdown': {status: count for status, count in status_counts},
        'total_value': total_value,
        'recent_quotes': recent_quotes
    }


def check_expired_quotes(db: Session) -> List[Quote]:
    """
    Check for expired quotes and update their status
    
    Args:
        db: Database session
        
    Returns:
        List[Quote]: List of quotes that were marked as expired
    """
    expired_quotes = db.query(Quote).filter(
        and_(
            Quote.status == 'sent',
            Quote.expiry_date < date.today()
        )
    ).all()
    
    for quote in expired_quotes:
        quote.status = 'expired'
        quote.updated_at = datetime.utcnow()
    
    if expired_quotes:
        db.commit()
    


# Quote History Services
def log_quote_history(
    db: Session,
    quote_id: int,
    user_id: Optional[int],
    event_type: str,
    event_category: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional['QuoteHistory']:
    """Log a quote history event."""
    from app.models.quote import QuoteHistory
    
    history_entry = QuoteHistory(
        quote_id=quote_id,
        user_id=user_id,
        event_type=event_type,
        event_category=event_category,
        description=description,
        event_metadata=metadata
    )
    db.add(history_entry)
    db.commit()
    return history_entry


def safe_log_quote_history(
    db: Session,
    quote_id: int,
    user_id: Optional[int],
    event_type: str,
    event_category: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Optional['QuoteHistory']:
    """Safely log quote history without affecting main operations."""
    try:
        return log_quote_history(
            db=db,
            quote_id=quote_id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            description=description,
            metadata=metadata
        )
    except Exception as e:
        print(f"Failed to log quote history: {e}")
        db.rollback()
        return None
    return expired_quotes