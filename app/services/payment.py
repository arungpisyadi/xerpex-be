"""
Payment services for the XerpeX ERP System
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.payment import Payment, Invoice, InvoiceItem
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentStatusUpdate,
    PaymentInvoiceCreate, PaymentInvoiceUpdate
)
from app.services.booking import get_booking
from app.utils.helpers import generate_invoice_number
from app.utils.sentry import sentry_monitored_service


@sentry_monitored_service
def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    """
    Get a payment by ID
    
    Args:
        db: Database session
        payment_id: Payment ID
        
    Returns:
        Payment: Payment or None
    """
    return db.query(Payment).filter(Payment.id == payment_id).first()


@sentry_monitored_service
def get_payments(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[Payment]:
    """
    Get payments with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        booking_id: Filter by booking ID
        status: Filter by status
        payment_method: Filter by payment method
        from_date: Filter by payment date from
        to_date: Filter by payment date to
        
    Returns:
        List[Payment]: List of payments
    """
    query = db.query(Payment)
    
    if booking_id:
        query = query.filter(Payment.booking_id == booking_id)
    
    if status:
        query = query.filter(Payment.status == status)
    
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    if from_date:
        query = query.filter(Payment.payment_date >= from_date)
    
    if to_date:
        query = query.filter(Payment.payment_date <= to_date)
    
    return query.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()


@sentry_monitored_service
def create_payment(db: Session, payment: PaymentCreate, current_user_id: int) -> Payment:
    """
    Create a new payment
    
    Args:
        db: Database session
        payment: Payment data
        current_user_id: Current user ID
        
    Returns:
        Payment: Created payment
        
    Raises:
        HTTPException: If booking not found
    """
    # Check if booking exists
    booking = get_booking(db, payment.booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {payment.booking_id} not found"
        )
    
    # Create payment
    db_payment = Payment(
        booking_id=payment.booking_id,
        amount=payment.amount,
        payment_method=payment.payment_method,
        payment_date=payment.payment_date,
        status="pending",
        notes=payment.notes,
        created_by=current_user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


@sentry_monitored_service
def update_payment(db: Session, payment_id: int, payment_update: PaymentUpdate) -> Payment:
    """
    Update a payment
    
    Args:
        db: Database session
        payment_id: Payment ID
        payment_update: Payment update data
        
    Returns:
        Payment: Updated payment
        
    Raises:
        HTTPException: If payment not found
    """
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Update payment fields
    update_data = payment_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_payment, key, value)
    
    db_payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


@sentry_monitored_service
def update_payment_status(db: Session, payment_id: int, status_update: PaymentStatusUpdate) -> Payment:
    """
    Update a payment status
    
    Args:
        db: Database session
        payment_id: Payment ID
        status_update: Payment status update data
        
    Returns:
        Payment: Updated payment
        
    Raises:
        HTTPException: If payment not found or invalid status
    """
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Validate status
    valid_statuses = ["pending", "paid", "failed", "refunded"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    db_payment.status = status_update.status
    db_payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


@sentry_monitored_service
def delete_payment(db: Session, payment_id: int) -> bool:
    """
    Delete a payment
    
    Args:
        db: Database session
        payment_id: Payment ID
        
    Returns:
        bool: True if payment was deleted
        
    Raises:
        HTTPException: If payment not found
    """
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    db.delete(db_payment)
    db.commit()
    
    return True


@sentry_monitored_service
def get_invoice(db: Session, invoice_id: int) -> Optional[Invoice]:
    """
    Get an invoice by ID
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        
    Returns:
        PaymentInvoice: Invoice or None
    """
    return db.query(PaymentInvoice).filter(PaymentInvoice.id == invoice_id).first()


@sentry_monitored_service
def get_invoice_by_number(db: Session, invoice_number: str) -> Optional[Invoice]:
    """
    Get an invoice by number
    
    Args:
        db: Database session
        invoice_number: Invoice number
        
    Returns:
        PaymentInvoice: Invoice or None
    """
    return db.query(PaymentInvoice).filter(PaymentInvoice.invoice_number == invoice_number).first()


@sentry_monitored_service
def get_invoices(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    booking_id: Optional[int] = None,
    status: Optional[str] = None,
    guest_name: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None
) -> List[Invoice]:
    """
    Get invoices with optional filtering
    
    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        booking_id: Filter by booking ID
        status: Filter by status
        guest_name: Filter by guest name
        from_date: Filter by due date from
        to_date: Filter by due date to
        
    Returns:
        List[Invoice]: List of invoices
    """
    query = db.query(Invoice)
    
    if booking_id:
        query = query.filter(Invoice.booking_id == booking_id)
    
    if status:
        query = query.filter(Invoice.status == status)
    
    if guest_name:
        query = query.filter(Invoice.guest_name.ilike(f"%{guest_name}%"))
    
    if from_date:
        query = query.filter(Invoice.due_date >= from_date)
    
    if to_date:
        query = query.filter(Invoice.due_date <= to_date)
    
    return query.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()


@sentry_monitored_service
def create_invoice(db: Session, invoice: PaymentInvoiceCreate, current_user_id: int) -> Invoice:
    """
    Create a new invoice
    
    Args:
        db: Database session
        invoice: Invoice data
        current_user_id: Current user ID
        
    Returns:
        Invoice: Created invoice
        
    Raises:
        HTTPException: If booking not found or items are invalid
    """
    # Check if booking exists
    booking = get_booking(db, invoice.booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {invoice.booking_id} not found"
        )
    
    # Validate items
    if not invoice.items or len(invoice.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice must have at least one item"
        )
    
    # Calculate total amount
    total_amount = Decimal('0.00')
    for item in invoice.items:
        if 'price' not in item or 'quantity' not in item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each item must have price and quantity"
            )
        total_amount += Decimal(str(item['price'])) * Decimal(str(item['quantity']))
    
    # Create invoice
    invoice_number = generate_invoice_number()
    db_invoice = Invoice(
        invoice_number=invoice_number,
        booking_id=invoice.booking_id,
        guest_name=invoice.guest_name,
        guest_email=invoice.guest_email,
        guest_phone=invoice.guest_phone,
        due_date=invoice.due_date,
        total_amount=total_amount,
        status="pending",
        notes=invoice.notes,
        created_by=current_user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_invoice)
    db.commit()
    db.refresh(db_invoice)
    
    # Add invoice items
    for item in invoice.items:
        db_item = InvoiceItem(
            invoice_id=db_invoice.id,
            description=item.get('description', ''),
            price=Decimal(str(item['price'])),
            quantity=int(item['quantity']),
            subtotal=Decimal(str(item['price'])) * Decimal(str(item['quantity']))
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@sentry_monitored_service
def update_invoice(db: Session, invoice_id: int, invoice_update: PaymentInvoiceUpdate) -> Invoice:
    """
    Update an invoice
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        invoice_update: Invoice update data
        
    Returns:
        Invoice: Updated invoice
        
    Raises:
        HTTPException: If invoice not found or items are invalid
    """
    db_invoice = get_invoice(db, invoice_id)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Update invoice fields
    update_data = invoice_update.dict(exclude_unset=True)
    
    # Handle items separately
    items = update_data.pop('items', None)
    
    for key, value in update_data.items():
        setattr(db_invoice, key, value)
    
    # Update items if provided
    if items is not None:
        # Validate items
        if not items or len(items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invoice must have at least one item"
            )
        
        # Calculate total amount
        total_amount = Decimal('0.00')
        for item in items:
            if 'price' not in item or 'quantity' not in item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Each item must have price and quantity"
                )
            total_amount += Decimal(str(item['price'])) * Decimal(str(item['quantity']))
        
        # Delete existing items
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
        
        # Add new items
        for item in items:
            db_item = InvoiceItem(
                invoice_id=db_invoice.id,
                description=item.get('description', ''),
                price=Decimal(str(item['price'])),
                quantity=int(item['quantity']),
                subtotal=Decimal(str(item['price'])) * Decimal(str(item['quantity']))
            )
            db.add(db_item)
        
        # Update total amount
        db_invoice.total_amount = total_amount
    
    db_invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@sentry_monitored_service
def update_invoice_status(db: Session, invoice_id: int, status: str) -> Invoice:
    """
    Update an invoice status
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        status: New status
        
    Returns:
        Invoice: Updated invoice
        
    Raises:
        HTTPException: If invoice not found or invalid status
    """
    db_invoice = get_invoice(db, invoice_id)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Validate status
    valid_statuses = ["pending", "paid", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    db_invoice.status = status
    db_invoice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_invoice)
    
    return db_invoice


@sentry_monitored_service
def delete_invoice(db: Session, invoice_id: int) -> bool:
    """
    Delete an invoice
    
    Args:
        db: Database session
        invoice_id: Invoice ID
        
    Returns:
        bool: True if invoice was deleted
        
    Raises:
        HTTPException: If invoice not found
    """
    db_invoice = get_invoice(db, invoice_id)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Delete invoice items
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
    
    # Delete invoice
    db.delete(db_invoice)
    db.commit()
    
    return True


@sentry_monitored_service
def get_payment_details(db: Session, payment_id: int) -> Dict[str, Any]:
    """
    Get payment details with related information
    
    Args:
        db: Database session
        payment_id: Payment ID
        
    Returns:
        Dict[str, Any]: Payment details
        
    Raises:
        HTTPException: If payment not found
    """
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Get booking
    booking = get_booking(db, db_payment.booking_id)
    
    # Get invoice if exists
    invoice = None
    if db_payment.invoice_id:
        invoice = get_invoice(db, db_payment.invoice_id)
    
    # Create result
    result = {
        "payment": db_payment,
        "invoice": invoice,
        "booking_code": booking.booking_code if booking else None,
        "guest_name": booking.guest_name if booking else None
    }
    
    return result


@sentry_monitored_service
def link_payment_to_invoice(db: Session, payment_id: int, invoice_id: int) -> Payment:
    """
    Link a payment to an invoice
    
    Args:
        db: Database session
        payment_id: Payment ID
        invoice_id: Invoice ID
        
    Returns:
        Payment: Updated payment
        
    Raises:
        HTTPException: If payment or invoice not found
    """
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    db_invoice = get_invoice(db, invoice_id)
    if not db_invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if payment and invoice belong to the same booking
    if db_payment.booking_id != db_invoice.booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment and invoice must belong to the same booking"
        )
    
    db_payment.invoice_id = invoice_id
    db_payment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_payment)
    
    return db_payment


@sentry_monitored_service
def get_booking_payment_summary(db: Session, booking_id: int) -> Dict[str, Any]:
    """
    Get payment summary for a booking
    
    Args:
        db: Database session
        booking_id: Booking ID
        
    Returns:
        Dict[str, Any]: Payment summary
        
    Raises:
        HTTPException: If booking not found
    """
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Get total invoiced amount
    total_invoiced = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.booking_id == booking_id,
        Invoice.status != "cancelled"
    ).scalar() or Decimal('0.00')
    
    # Get total paid amount
    total_paid = db.query(func.sum(Payment.amount)).filter(
        Payment.booking_id == booking_id,
        Payment.status == "paid"
    ).scalar() or Decimal('0.00')
    
    # Get pending payments
    pending_payments = db.query(func.sum(Payment.amount)).filter(
        Payment.booking_id == booking_id,
        Payment.status == "pending"
    ).scalar() or Decimal('0.00')
    
    # Calculate balance
    balance = total_invoiced - total_paid
    
    # Get all payments
    payments = get_payments(db, booking_id=booking_id)
    
    # Get all invoices
    invoices = get_invoices(db, booking_id=booking_id)
    
    # Create result
    result = {
        "booking_id": booking_id,
        "booking_code": booking.booking_code,
        "guest_name": booking.guest_name,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "pending_payments": pending_payments,
        "balance": balance,
        "payments": payments,
        "invoices": invoices
    }
    
    return result