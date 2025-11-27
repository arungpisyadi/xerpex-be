"""
Payment and Invoice services for the XerpeX ERP System
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.payment import Invoice, InvoiceItem, Payment, InvoiceHistory
from app.models.customer import Customer
from app.models.package import Package
from app.models.quote import Quote, QuoteItem
from app.models.user import User
from app.schemas.payment import (
    InvoiceCreate, InvoiceUpdate, InvoiceStatusUpdate, InvoiceNotesUpdate,
    PaymentCreate, PaymentUpdate, PaymentStatusUpdate,
    QuoteToInvoiceRequest, InvoiceStatus, PaymentStatus, PaymentMethod, PaymentType
)
from app.services.customer import get_customer
from app.services.package import get_package
from app.utils.helpers import generate_invoice_number
from app.utils.security import get_user_filter_condition, should_apply_user_isolation


# Invoice Services
def get_invoice(db: Session, invoice_id: int, current_user: User) -> Optional[Invoice]:
    """
    Get an invoice by ID with role-based user isolation
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Invoice: Invoice or None
    """
    query = db.query(Invoice).options(
        joinedload(Invoice.customer),
        joinedload(Invoice.items).joinedload(InvoiceItem.package),
        joinedload(Invoice.payments)
    ).filter(Invoice.id == invoice_id)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Invoice.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.first()


def get_invoice_by_number(db: Session, invoice_number: str, user_id: int) -> Optional[Invoice]:
    """
    Get an invoice by number with user isolation
    
    Args:
        db: Database session
        invoice_number: Invoice number
        user_id: Current user ID for isolation
        
    Returns:
        Invoice: Invoice or None
    """
    return db.query(Invoice).options(
        joinedload(Invoice.customer),
        joinedload(Invoice.items).joinedload(InvoiceItem.package),
        joinedload(Invoice.payments)
    ).filter(
        and_(Invoice.invoice_number == invoice_number, Invoice.user_id == user_id)
    ).first()


def get_invoices(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[int] = None,
    search: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    overdue_only: bool = False
) -> List[Invoice]:
    """
    Get invoices with optional filtering and search (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by invoice status
        customer_id: Filter by customer ID
        search: Search by invoice number or customer name
        from_date: Filter by issue date from
        to_date: Filter by issue date to
        overdue_only: Filter only overdue invoices
        
    Returns:
        List[Invoice]: List of invoices
    """
    query = db.query(Invoice).options(
        joinedload(Invoice.customer)
    )
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Invoice.user_id)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    # Apply filters
    if status:
        query = query.filter(Invoice.status == status)
    
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    
    if search:
        query = query.join(Customer).filter(
            or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Customer.name.ilike(f"%{search}%")
            )
        )
    
    if from_date:
        query = query.filter(Invoice.issue_date >= from_date)
    
    if to_date:
        query = query.filter(Invoice.issue_date <= to_date)
    
    if overdue_only:
        query = query.filter(
            and_(
                Invoice.status.in_(['sent', 'overdue']),
                Invoice.due_date < date.today()
            )
        )
    
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


def create_invoice(db: Session, invoice: InvoiceCreate, current_user: User) -> Invoice:
    """
    Create a new invoice with items
    
    Args:
        db: Database session
        invoice: Invoice data
        current_user: Current user for isolation and validation
        
    Returns:
        Invoice: Created invoice
        
    Raises:
        HTTPException: If customer not found or validation fails
    """
    # Validate customer exists and belongs to user
    customer = get_customer(db, invoice.customer_id, current_user)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Generate invoice number
    invoice_number = generate_invoice_number()
    
    # Ensure invoice number is unique
    while db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first():
        invoice_number = generate_invoice_number()
    
    # Create invoice
    db_invoice = Invoice(
        user_id=current_user.id,
        customer_id=invoice.customer_id,
        booking_id=None,  # Set to None for now as it's optional
        invoice_number=invoice_number,
        quote_id=invoice.quote_id,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        status=invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
        payment_terms=invoice.payment_terms,
        notes=invoice.notes,
        total=Decimal('0.00'),
        tax_total=invoice.tax_total,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_invoice)
    db.flush()  # Get the invoice ID
    
    # Add invoice items
    total_amount = Decimal('0.00')
    for item_data in invoice.items:
        # Validate package exists and belongs to user
        package = get_package(db, item_data.package_id)
        if not package or package.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Package with ID {item_data.package_id} not found"
            )
        
        # Create invoice item
        invoice_item = InvoiceItem(
            invoice_id=db_invoice.id,
            package_id=item_data.package_id,
            unit_price=item_data.unit_price,
            discount=item_data.discount,
            pax=item_data.pax,
            line_total=item_data.line_total,
            created_at=datetime.utcnow()
        )
        
        db.add(invoice_item)
        total_amount += item_data.line_total
    
    # Update invoice total
    db_invoice.total = total_amount + invoice.tax_total
    
    db.commit()
    db.refresh(db_invoice)
    
    # Log history event
    safe_log_invoice_history(
        db=db,
        invoice_id=db_invoice.id,
        user_id=current_user.id,
        event_type="invoice_created",
        event_category="lifecycle",
        description="Invoice created",
        metadata={
            "total_amount": str(db_invoice.total),
            "customer_name": customer.name,
            "status": db_invoice.status
        }
    )
    
    return db_invoice


def update_invoice(
    db: Session,
    invoice_id: int,
    invoice_update: InvoiceUpdate,
    user_id: int
) -> Invoice:
    """
    Update an invoice
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        invoice_update: Invoice update data
        user_id: Current user ID for isolation
        
    Returns:
        Invoice: Updated invoice
        
    Raises:
        HTTPException: If invoice not found or validation fails
    """
    # Create a temporary user object for the internal call
    # This is a workaround until we fully update all functions to use User objects
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_invoice = get_invoice(db, invoice_id, temp_user)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if invoice can be modified
    if db_invoice.status in ['paid', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify invoice with status '{db_invoice.status}'"
        )
    
    # Update invoice fields
    update_data = invoice_update.dict(exclude_unset=True, exclude={'items'})
    
    # Validate customer if being updated
    if 'customer_id' in update_data:
        customer = get_customer(db, update_data['customer_id'], temp_user)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
    
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    # Update items if provided
    if invoice_update.items is not None:
        # Delete existing items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
        
        # Add new items
        total_amount = Decimal('0.00')
        for item_data in invoice_update.items:
            # Validate package
            package = get_package(db, item_data.package_id)
            if not package or package.user_id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Package with ID {item_data.package_id} not found"
                )
            
            invoice_item = InvoiceItem(
                invoice_id=db_invoice.id,
                package_id=item_data.package_id,
                unit_price=item_data.unit_price,
                discount=item_data.discount,
                pax=item_data.pax,
                line_total=item_data.line_total,
                created_at=datetime.utcnow()
            )
            
            db.add(invoice_item)
            total_amount += item_data.line_total
        
        # Update total
        db_invoice.total = total_amount + (db_invoice.tax_total or Decimal('0.00'))
    
    db_invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


def update_invoice_status(
    db: Session,
    invoice_id: int,
    status_update: InvoiceStatusUpdate,
    user_id: int
) -> Invoice:
    """
    Update invoice status with workflow validation
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        status_update: Status update data
        user_id: Current user ID for isolation
        
    Returns:
        Invoice: Updated invoice (with status changed only if transition is valid)
        
    Raises:
        HTTPException: If invoice not found
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_invoice = get_invoice(db, invoice_id, temp_user)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Validate status transitions
    valid_transitions = {
        'draft': ['sent', 'cancelled'],
        'sent': ['paid', 'overdue', 'cancelled'],
        'overdue': ['paid', 'cancelled'],
        'paid': [],  # Terminal state
        'cancelled': ['draft']  # Can be reopened
    }
    
    status_value = status_update.status.value if hasattr(status_update.status, 'value') else str(status_update.status)
    
    # Check if transition is valid
    valid_transition = status_value in valid_transitions.get(db_invoice.status, [])
    
    if valid_transition:
        # Only update status if transition is valid
        old_status = db_invoice.status
        db_invoice.status = status_value
        db_invoice.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_invoice)
        
        # Log history event for successful status change
        event_type = "status_changed"
        event_category = "status"
        description = f"Invoice status changed from '{old_status}' to '{status_value}'"
        
        # Use more specific event types for workflow actions
        if status_value == "sent":
            event_type = "invoice_sent"
            event_category = "workflow"
            description = "Invoice sent to customer"
        elif status_value == "cancelled":
            event_type = "invoice_cancelled"
            event_category = "workflow"
            description = "Invoice cancelled"
        elif status_value == "draft" and old_status == "cancelled":
            event_type = "invoice_reopened"
            event_category = "workflow"
            description = "Invoice reopened from cancelled status"
        elif status_value == "paid":
            event_type = "fully_paid"
            event_category = "payment"
            description = "Invoice marked as fully paid"
        
        safe_log_invoice_history(
            db=db,
            invoice_id=db_invoice.id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            description=description,
            metadata={
                "old_status": old_status,
                "new_status": status_value
            }
        )
    else:
        # Invalid transition: keep current status, skip status update
        # Don't throw exception - allow process to continue for email sending
        # Log attempted invalid transition
        safe_log_invoice_history(
            db=db,
            invoice_id=db_invoice.id,
            user_id=user_id,
            event_type="invalid_status_transition_attempted",
            event_category="workflow",
            description=f"Invalid status transition attempted from '{db_invoice.status}' to '{status_value}' - status unchanged",
            metadata={
                "attempted_status": status_value,
                "current_status": db_invoice.status,
                "valid_transitions": valid_transitions.get(db_invoice.status, [])
            }
        )
    
    return db_invoice


def update_invoice_notes(
    db: Session,
    invoice_id: int,
    notes_update: InvoiceNotesUpdate,
    user_id: int
) -> Invoice:
    """
    Update invoice notes only
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        notes_update: Notes update data
        user_id: Current user ID for isolation
        
    Returns:
        Invoice: Updated invoice
        
    Raises:
        HTTPException: If invoice not found or validation fails
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_invoice = get_invoice(db, invoice_id, temp_user)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if invoice can be modified
    if db_invoice.status in ['paid', 'cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot modify invoice with status '{db_invoice.status}'"
        )
    
    # Store old notes for history logging
    old_notes = db_invoice.notes
    
    # Update notes field
    db_invoice.notes = notes_update.notes
    db_invoice.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_invoice)
    
    # Log history event for notes update
    safe_log_invoice_history(
        db=db,
        invoice_id=db_invoice.id,
        user_id=user_id,
        event_type="notes_updated",
        event_category="workflow",
        description="Invoice notes updated",
        metadata={
            "old_notes": old_notes,
            "new_notes": notes_update.notes
        }
    )
    
    return db_invoice


def delete_invoice(db: Session, invoice_id: int, user_id: int) -> bool:
    """
    Delete an invoice
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        user_id: Current user ID for isolation
        
    Returns:
        bool: True if invoice was deleted
        
    Raises:
        HTTPException: If invoice not found or cannot be deleted
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=user_id, role='user')  # Default to regular user for isolation
    db_invoice = get_invoice(db, invoice_id, temp_user)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Only allow deletion of draft invoices
    if db_invoice.status != 'draft':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft invoices can be deleted"
        )
    
    # Check if invoice has payments
    if db_invoice.payments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete invoice with payments"
        )
    
    db.delete(db_invoice)
    db.commit()
    
    return True


# Payment Services
def get_payment(db: Session, payment_id: int, current_user: User) -> Optional[Payment]:
    """
    Get a payment by ID with role-based user isolation
    
    Args:
        db: Database session
        payment_id: Payment ID
        current_user: Current user (for role-based access control)
        
    Returns:
        Payment: Payment or None
    """
    query = db.query(Payment).options(
        joinedload(Payment.invoice).joinedload(Invoice.customer)
    ).filter(Payment.id == payment_id)
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Payment.created_by)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    return query.first()


def get_payments(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100,
    invoice_id: Optional[int] = None,
    status: Optional[PaymentStatus] = None,
    payment_method: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[Payment]:
    """
    Get payments with optional filtering (role-based user isolation)
    
    Args:
        db: Database session
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        invoice_id: Filter by invoice ID
        status: Filter by payment status
        payment_method: Filter by payment method
        from_date: Filter by payment date from
        to_date: Filter by payment date to
        
    Returns:
        List[Payment]: List of payments
    """
    query = db.query(Payment).options(
        joinedload(Payment.invoice).joinedload(Invoice.customer)
    )
    
    # Apply user isolation based on role
    user_filter = get_user_filter_condition(current_user, Payment.created_by)
    if user_filter is not True:  # True means no filter (admin/finance)
        query = query.filter(user_filter)
    
    # Apply filters
    if invoice_id:
        query = query.filter(Payment.invoice_id == invoice_id)
    
    if status:
        query = query.filter(Payment.status == status)
    
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    if from_date:
        query = query.filter(Payment.payment_date >= from_date)
    
    if to_date:
        query = query.filter(Payment.payment_date <= to_date)
    
    return query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()


def create_payment(db: Session, payment: PaymentCreate, created_by: int) -> Payment:
    """
    Create a new payment
    
    Args:
        db: Database session
        payment: Payment data
        created_by: Current user ID for isolation
        
    Returns:
        Payment: Created payment
        
    Raises:
        HTTPException: If invoice not found or validation fails
    """
    # Validate invoice exists and belongs to user
    # Get the actual user from database to check their role
    from app.models.user import User
    actual_user = db.query(User).filter(User.id == created_by).first()
    if not actual_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Use actual user for invoice lookup (respects admin privileges)
    invoice = get_invoice(db, payment.invoice_id, actual_user)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if invoice can receive payments
    if invoice.status in ['cancelled']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add payment to cancelled invoice"
        )
    
    # Create payment
    db_payment = Payment(
        created_by=created_by,
        invoice_id=payment.invoice_id,
        booking_id=payment.booking_id if hasattr(payment, 'booking_id') else None,
        amount=payment.amount,
        payment_method=payment.payment_method.value if isinstance(payment.payment_method, PaymentMethod) else payment.payment_method,
        payment_type=payment.payment_type.value if hasattr(payment, 'payment_type') and payment.payment_type else None,
        payment_date=payment.payment_date,
        reference_number=payment.reference_number,
        status=payment.status.value if hasattr(payment, 'status') and payment.status else PaymentStatus.pending.value,
        notes=payment.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Update invoice status based on payment status and type
    if (db_payment.status == PaymentStatus.partial.value or
        db_payment.payment_type in ["down-payment", "installment"]):
        # Update invoice to partially_paid
        db_payment.invoice.status = InvoiceStatus.partially_paid.value
    elif (db_payment.status == PaymentStatus.full.value or
          db_payment.payment_type == "paid-off"):
        # Update invoice to paid
        db_payment.invoice.status = InvoiceStatus.paid.value
    
    db.commit()
    db.refresh(db_payment)
    
    # Log history event for payment creation
    safe_log_invoice_history(
        db=db,
        invoice_id=payment.invoice_id,
        user_id=created_by,
        event_type="payment_added",
        event_category="payment",
        description=f"Payment of ${payment.amount} added",
        metadata={
            "payment_id": db_payment.id,
            "amount": str(payment.amount),
            "payment_method": payment.payment_method.value if isinstance(payment.payment_method, PaymentMethod) else payment.payment_method,
            "reference_number": payment.reference_number
        },
        payment_id=db_payment.id
    )
    
    return db_payment


def update_payment(
    db: Session,
    payment_id: int,
    payment_update: PaymentUpdate,
    created_by: int
) -> Payment:
    """
    Update a payment
    
    Args:
        db: Database session
        payment_id: Payment ID
        payment_update: Payment update data
        created_by: Current user ID for isolation
        
    Returns:
        Payment: Updated payment
        
    Raises:
        HTTPException: If payment not found
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=created_by, role='user')  # Default to regular user for isolation
    db_payment = get_payment(db, payment_id, temp_user)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Check if payment can be modified
    if db_payment.status == PaymentStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify completed payment"
        )
    
    # Update payment fields
    update_data = payment_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    db_payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


def update_payment_status(
    db: Session,
    payment_id: int,
    status_update: PaymentStatusUpdate,
    created_by: int
) -> Payment:
    """
    Update payment status
    
    Args:
        db: Database session
        payment_id: Payment ID
        status_update: Status update data
        created_by: Current user ID for isolation
        
    Returns:
        Payment: Updated payment
        
    Raises:
        HTTPException: If payment not found
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=created_by, role='user')  # Default to regular user for isolation
    db_payment = get_payment(db, payment_id, temp_user)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    old_status = db_payment.status
    db_payment.status = status_update.status
    db_payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_payment)
    
    # Log history event for payment status change
    event_type = "payment_status_changed"
    description = f"Payment status changed from '{old_status}' to '{status_update.status}'"
    
    # Use more specific event types
    if status_update.status == PaymentStatus.completed:
        event_type = "payment_completed"
        description = f"Payment of ${db_payment.amount} completed"
    elif status_update.status == PaymentStatus.failed:
        event_type = "payment_failed"
        description = f"Payment of ${db_payment.amount} failed"
    
    safe_log_invoice_history(
        db=db,
        invoice_id=db_payment.invoice_id,
        user_id=created_by,
        event_type=event_type,
        event_category="payment",
        description=description,
        metadata={
            "payment_id": db_payment.id,
            "amount": str(db_payment.amount),
            "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
            "new_status": status_update.status.value if hasattr(status_update.status, 'value') else str(status_update.status)
        },
        payment_id=db_payment.id
    )
    
    # Update invoice payment status (handles partial/full payment)
    _update_invoice_payment_status(db, db_payment.invoice)
    
    return db_payment


def delete_payment(db: Session, payment_id: int, created_by: int) -> bool:
    """
    Delete a payment
    
    Args:
        db: Database session
        payment_id: Payment ID
        created_by: Current user ID for isolation
        
    Returns:
        bool: True if payment was deleted
        
    Raises:
        HTTPException: If payment not found or cannot be deleted
    """
    # Create a temporary user object for the internal call
    from app.models.user import User
    temp_user = User(id=created_by, role='user')  # Default to regular user for isolation
    db_payment = get_payment(db, payment_id, temp_user)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Only allow deletion of pending payments
    if db_payment.status != PaymentStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending payments can be deleted"
        )
    
    invoice = db_payment.invoice
    db.delete(db_payment)
    db.commit()
    
    # Update invoice payment status
    _update_invoice_payment_status(db, invoice)
    
    return True


# Quote to Invoice Conversion
def convert_quote_to_invoice(
    db: Session,
    conversion_request: QuoteToInvoiceRequest,
    user_id: int
) -> Invoice:
    """
    Convert a quote to an invoice
    
    Args:
        db: Database session
        conversion_request: Conversion request data
        user_id: Current user ID for isolation
        
    Returns:
        Invoice: Created invoice
        
    Raises:
        HTTPException: If quote not found or cannot be converted
    """
    # Get quote
    quote = db.query(Quote).options(
        joinedload(Quote.items).joinedload(QuoteItem.package)
    ).filter(
        and_(Quote.id == conversion_request.quote_id, Quote.user_id == user_id)
    ).first()
    
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quote not found"
        )
    
    # Check if quote can be converted
    if quote.status != 'accepted':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only accepted quotes can be converted to invoices"
        )
    
    # Check if quote is already converted
    existing_invoice = db.query(Invoice).filter(Invoice.quote_id == quote.id).first()
    if existing_invoice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote has already been converted to an invoice"
        )
    
    # Generate invoice number
    invoice_number = generate_invoice_number()
    while db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first():
        invoice_number = generate_invoice_number()
    
    # Create invoice from quote
    db_invoice = Invoice(
        user_id=user_id,
        customer_id=quote.customer_id,
        invoice_number=invoice_number,
        quote_id=quote.id,
        issue_date=conversion_request.issue_date,
        due_date=conversion_request.due_date,
        status=InvoiceStatus.draft,
        total=quote.total,
        tax_total=quote.tax_total,
        notes=conversion_request.notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_invoice)
    db.flush()
    
    # Copy quote items to invoice items
    for quote_item in quote.items:
        invoice_item = InvoiceItem(
            invoice_id=db_invoice.id,
            package_id=quote_item.package_id,
            unit_price=quote_item.unit_price,
            discount=quote_item.discount,
            line_total=quote_item.line_total,
            pax=quote_item.pax,
            created_at=datetime.utcnow()
        )
        db.add(invoice_item)
    
    db.commit()
    db.refresh(db_invoice)
    
    # Log history event for quote conversion
    safe_log_invoice_history(
        db=db,
        invoice_id=db_invoice.id,
        user_id=user_id,
        event_type="invoice_converted_from_quote",
        event_category="lifecycle",
        description=f"Invoice created from accepted quote #{quote.quote_number}",
        metadata={
            "quote_id": quote.id,
            "quote_number": quote.quote_number,
            "total_amount": str(db_invoice.total)
        }
    )
    
    return db_invoice


# Helper Functions
def _update_invoice_payment_status(db: Session, invoice: Invoice) -> None:
    """
    Update invoice status based on payments
    
    Args:
        db: Database session
        invoice: Invoice to update
    """
    if not invoice:
        return
    
    # Calculate total paid amount
    total_paid = db.query(func.sum(Payment.amount)).filter(
        and_(
            Payment.invoice_id == invoice.id,
            Payment.status == PaymentStatus.completed
        )
    ).scalar() or Decimal('0.00')
    
    # Update invoice status based on payment
    if total_paid >= invoice.total:
        invoice.status = InvoiceStatus.paid
    elif invoice.due_date < date.today() and invoice.status == InvoiceStatus.sent:
        invoice.status = InvoiceStatus.overdue
    
    invoice.updated_at = datetime.utcnow()
    db.commit()


def check_overdue_invoices(db: Session) -> List[Invoice]:
    """
    Check for overdue invoices and update their status
    
    Args:
        db: Database session
        
    Returns:
        List[Invoice]: List of invoices that were marked as overdue
    """
    overdue_invoices = db.query(Invoice).filter(
        and_(
            Invoice.status == InvoiceStatus.sent,
            Invoice.due_date < date.today()
        )
    ).all()
    
    for invoice in overdue_invoices:
        invoice.status = InvoiceStatus.overdue
        invoice.updated_at = datetime.utcnow()
    
    if overdue_invoices:
        db.commit()
    
    return overdue_invoices


def get_invoice_statistics(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get invoice statistics for dashboard
    
    Args:
        db: Database session
        user_id: Current user ID for isolation
        
    Returns:
        Dict: Invoice statistics
    """
    total_invoices = db.query(Invoice).filter(Invoice.user_id == user_id).count()
    
    status_counts = db.query(
        Invoice.status,
        func.count(Invoice.id).label('count')
    ).filter(Invoice.user_id == user_id).group_by(Invoice.status).all()
    
    # Calculate total value
    total_value = db.query(
        func.sum(Invoice.total)
    ).filter(Invoice.user_id == user_id).scalar() or Decimal('0.00')
    
    # Calculate overdue
    overdue_count = db.query(Invoice).filter(
        and_(
            Invoice.user_id == user_id,
            Invoice.status == InvoiceStatus.overdue
        )
    ).count()
    
    overdue_value = db.query(
        func.sum(Invoice.total)
    ).filter(
        and_(
            Invoice.user_id == user_id,
            Invoice.status == InvoiceStatus.overdue
        )
    ).scalar() or Decimal('0.00')
    
    return {
        'total_invoices': total_invoices,
        'status_breakdown': {status: count for status, count in status_counts},
        'total_value': total_value,
        'overdue_count': overdue_count,
        'overdue_value': overdue_value
    }


def get_payment_statistics(db: Session, created_by: int) -> Dict[str, Any]:
    """
    Get payment statistics for dashboard
    
    Args:
        db: Database session
        created_by: Current user ID for isolation
        
    Returns:
        Dict: Payment statistics
    """
    total_payments = db.query(Payment).filter(Payment.created_by == created_by).count()
    
    method_counts = db.query(
        Payment.payment_method,
        func.count(Payment.id).label('count')
    ).filter(Payment.created_by == created_by).group_by(Payment.payment_method).all()
    
    # Calculate total amount
    total_amount = db.query(
        func.sum(Payment.amount)
    ).filter(
        and_(
            Payment.created_by == created_by,
            Payment.status == PaymentStatus.completed
        )
    ).scalar() or Decimal('0.00')
    
    # Recent payments
    recent_payments = db.query(Payment).options(
        joinedload(Payment.invoice).joinedload(Invoice.customer)
    ).filter(Payment.created_by == created_by).order_by(
        Payment.created_at.desc()
    ).limit(5).all()
    
    return {
        'total_payments': total_payments,
        'method_breakdown': {method: count for method, count in method_counts},
        'total_amount': total_amount,
        'recent_payments': recent_payments
    }


# Invoice History Services
def log_invoice_history(
    db: Session,
    invoice_id: int,
    user_id: int,
    event_type: str,
    event_category: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    payment_id: Optional[int] = None
) -> Optional[InvoiceHistory]:
    """
    Log an invoice history event
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        user_id: User ID who performed the action
        event_type: Type of event (e.g., 'invoice_created', 'status_changed')
        event_category: Category of event ('lifecycle', 'status', 'workflow', 'payment')
        description: Human-readable description of the event
        metadata: Optional additional event metadata
        payment_id: Optional payment ID to link this history event to a payment
        
    Returns:
        InvoiceHistory: Created history record or None if failed
    """
    try:
        history_record = InvoiceHistory(
            invoice_id=invoice_id,
            user_id=user_id,
            payment_id=payment_id,
            event_type=event_type,
            event_category=event_category,
            description=description,
            event_metadata=metadata,
            created_at=datetime.utcnow()
        )
        
        db.add(history_record)
        db.commit()
        db.refresh(history_record)
        
        return history_record
    
    except Exception as e:
        # Log the error but don't break the main operation
        print(f"Failed to log invoice history: {e}")
        db.rollback()
        return None


def safe_log_invoice_history(
    db: Session,
    invoice_id: int,
    user_id: int,
    event_type: str,
    event_category: str,
    description: str,
    metadata: Optional[Dict[str, Any]] = None,
    payment_id: Optional[int] = None
) -> None:
    """
    Safely log invoice history event without breaking main operations
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        user_id: User ID who performed the action
        event_type: Type of event
        event_category: Category of event
        description: Description of the event
        metadata: Optional additional event metadata
        payment_id: Optional payment ID to link this history event to a payment
    """
    try:
        log_invoice_history(
            db=db,
            invoice_id=invoice_id,
            user_id=user_id,
            event_type=event_type,
            event_category=event_category,
            description=description,
            metadata=metadata,
            payment_id=payment_id
        )
    except Exception as e:
        # Log error but don't break main operation
        print(f"Failed to safely log invoice history: {e}")


def get_invoice_history(
    db: Session,
    invoice_id: int,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
    event_category: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> List[InvoiceHistory]:
    """
    Get invoice history with optional filtering and pagination
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        current_user: Current user (for role-based access control)
        skip: Number of records to skip
        limit: Maximum number of records to return
        event_category: Filter by event category
        from_date: Filter by date from
        to_date: Filter by date to
        
    Returns:
        List[InvoiceHistory]: List of history events
    """
    # First verify user has access to the invoice
    invoice = get_invoice(db, invoice_id, current_user)
    if not invoice:
        return []
    
    # Build query with joins to get user information
    query = db.query(InvoiceHistory).options(
        joinedload(InvoiceHistory.user),
        joinedload(InvoiceHistory.invoice)
    ).filter(InvoiceHistory.invoice_id == invoice_id)
    
    # Apply filters
    if event_category:
        query = query.filter(InvoiceHistory.event_category == event_category)
    
    if from_date:
        query = query.filter(InvoiceHistory.created_at >= datetime.combine(from_date, datetime.min.time()))
    
    if to_date:
        query = query.filter(InvoiceHistory.created_at <= datetime.combine(to_date, datetime.max.time()))
    
    # Order by created_at descending (newest first) and apply pagination
    return query.order_by(InvoiceHistory.created_at.desc()).offset(skip).limit(limit).all()


def count_invoice_history(
    db: Session,
    invoice_id: int,
    current_user: User,
    event_category: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
) -> int:
    """
    Count total invoice history events for pagination
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        current_user: Current user (for role-based access control)
        event_category: Filter by event category
        from_date: Filter by date from
        to_date: Filter by date to
        
    Returns:
        int: Total count of history events
    """
    # First verify user has access to the invoice
    invoice = get_invoice(db, invoice_id, current_user)
    if not invoice:
        return 0
    
    # Build query
    query = db.query(InvoiceHistory).filter(InvoiceHistory.invoice_id == invoice_id)
    
    # Apply filters
    if event_category:
        query = query.filter(InvoiceHistory.event_category == event_category)
    
    if from_date:
        query = query.filter(InvoiceHistory.created_at >= datetime.combine(from_date, datetime.min.time()))
    
    if to_date:
        query = query.filter(InvoiceHistory.created_at <= datetime.combine(to_date, datetime.max.time()))
    
    return query.count()