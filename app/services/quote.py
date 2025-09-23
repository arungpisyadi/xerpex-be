"""
Quote services for the XerpeX ERP System
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.quote import Quote, QuoteItem
from app.models.customer import Customer
from app.models.package import Package
from app.models.tax import Tax
from app.models.user import User
from app.schemas.quote import (
    QuoteCreate, QuoteUpdate, QuoteStatusUpdate, QuoteItemCreate,
    QuoteConversionRequest, QuoteStatus
)
from app.services.customer import get_customer
from app.services.package import get_package
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
        joinedload(Quote.items).joinedload(QuoteItem.package)
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
        joinedload(Quote.customer)
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
            line_total=item_data.line_total,
            created_at=datetime.utcnow()
        )
        
        db.add(quote_item)
        total_amount += item_data.line_total
    
    # Update quote totals
    db_quote.total = total_amount
    db_quote.tax_total = quote.tax_total
    
    db.commit()
    db.refresh(db_quote)
    
    return db_quote


def update_quote(
    db: Session, 
    quote_id: int, 
    quote_update: QuoteUpdate, 
    user_id: int
) -> Quote:
    """
    Update a quote
    
    Args:
        db: Database session
        quote_id: Quote ID
        quote_update: Quote update data
        user_id: Current user ID for isolation
        
    Returns:
        Quote: Updated quote
        
    Raises:
        HTTPException: If quote not found or validation fails
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_quote = get_quote(db, quote_id, temp_user)
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
    
    # Update quote fields
    update_data = quote_update.dict(exclude_unset=True, exclude={'items'})
    
    # Validate customer if being updated
    if 'customer_id' in update_data:
        # Create a temporary user object for the internal call
        from app.models.user import User
        temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
        customer = get_customer(db, update_data['customer_id'], temp_user)
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
    
    # Update items if provided
    if quote_update.items is not None:
        # Delete existing items
        db.query(QuoteItem).filter(QuoteItem.quote_id == quote_id).delete()
        
        # Add new items
        total_amount = Decimal('0.00')
        for item_data in quote_update.items:
            # Validate package
            package = get_package(db, item_data.package_id)
            if not package or package.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {item_data.package_id} not found"
                )
            
            quote_item = QuoteItem(
                quote_id=db_quote.id,
                package_id=item_data.package_id,
                unit_price=item_data.unit_price,
                discount=item_data.discount,
                line_total=item_data.line_total,
                created_at=datetime.utcnow()
            )
            
            db.add(quote_item)
            total_amount += item_data.line_total
        
        # Update totals
        db_quote.total = total_amount
    
    db_quote.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_quote)
    
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
    user_id: int
) -> Quote:
    """
    Update quote status with workflow validation
    
    Args:
        db: Database session
        quote_id: Quote ID
        status_update: Status update data
        user_id: Current user ID for isolation
        
    Returns:
        Quote: Updated quote
        
    Raises:
        HTTPException: If quote not found or invalid status transition
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_quote = get_quote(db, quote_id, temp_user)
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
    
    db_quote.status = status_update.status
    db_quote.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_quote)
    
    return db_quote


def delete_quote(db: Session, quote_id: int, user_id: int) -> bool:
    """
    Delete a quote
    
    Args:
        db: Database session
        quote_id: Quote ID
        user_id: Current user ID for isolation
        
    Returns:
        bool: True if quote was deleted
        
    Raises:
        HTTPException: If quote not found or cannot be deleted
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_quote = get_quote(db, quote_id, temp_user)
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
    
    if tax_ids:
        taxes = db.query(Tax).filter(
            and_(Tax.id.in_(tax_ids), Tax.user_id == user_id)
        ).all()
        
        return calculate_total_with_taxes(subtotal, taxes)
    
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
    
    return expired_quotes