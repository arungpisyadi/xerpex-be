"""
Test utilities for the XerpeX ERP System
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking, BookingVilla
from app.models.payment import Payment, Invoice, InvoiceItem


def create_test_villa(
    db: Session,
    name: str = "Test Villa",
    description: str = "Test villa description",
    base_price: Decimal = Decimal("1000000.00"),
    max_guests: int = 4,
    bedrooms: int = 2,
    bathrooms: int = 2,
    created_by: int = 1
) -> Villa:
    """
    Create a test villa
    """
    villa = Villa(
        name=name,
        description=description,
        base_price=base_price,
        max_guests=max_guests,
        bedrooms=bedrooms,
        bathrooms=bathrooms,
        created_by=created_by,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


def create_test_villa_availability(
    db: Session,
    villa_id: int,
    date_val: date,
    is_available: bool = True,
    blocked_reason: Optional[str] = None,
    updated_by: int = 1
) -> VillaAvailability:
    """
    Create a test villa availability
    """
    availability = VillaAvailability(
        villa_id=villa_id,
        date=date_val,
        is_available=is_available,
        blocked_reason=blocked_reason,
        updated_by=updated_by,
        updated_at=datetime.utcnow()
    )
    db.add(availability)
    db.commit()
    db.refresh(availability)
    return availability


def create_test_booking(
    db: Session,
    customer_id: int = 1,
    check_in: date = date.today() + timedelta(days=7),
    check_out: date = date.today() + timedelta(days=10),
    total_pax: int = 2,
    status: str = "pending",
    notes: Optional[str] = None,
    user_id: int = 1
) -> Booking:
    """
    Create a test booking
    """
    booking = Booking(
        user_id=user_id,
        customer_id=customer_id,
        booking_code=f"BK{datetime.now().strftime('%y%m%d')}TEST",
        check_in=check_in,
        check_out=check_out,
        total_pax=total_pax,
        status=status,
        notes=notes,
        total=Decimal('0.00'),
        tax_total=Decimal('0.00'),
        amount_paid=Decimal('0.00'),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def create_test_booking_villa(
    db: Session,
    booking_id: int,
    villa_id: int,
    check_in: date = date.today() + timedelta(days=7),
    check_out: date = date.today() + timedelta(days=10),
    nightly_rate: Decimal = Decimal("1000000.00")
) -> BookingVilla:
    """
    Create a test booking villa (simplified junction table)
    Note: check_in, check_out, and nightly_rate parameters are kept for
    backward compatibility but not used in the simplified model.
    """
    booking_villa = BookingVilla(
        booking_id=booking_id,
        villa_id=villa_id,
        created_at=datetime.utcnow()
    )
    db.add(booking_villa)
    db.commit()
    db.refresh(booking_villa)
    return booking_villa


def create_test_payment(
    db: Session,
    invoice_id: int,
    user_id: int = 1,
    amount: Decimal = Decimal("1000000.00"),
    payment_method: str = "bank_transfer",
    payment_date: date = date.today(),
    status: str = "pending",
    notes: Optional[str] = None,
    reference_number: Optional[str] = None
) -> Payment:
    """
    Create a test payment linked to an invoice
    """
    payment = Payment(
        user_id=user_id,
        invoice_id=invoice_id,
        amount=amount,
        payment_method=payment_method,
        payment_date=payment_date,
        status=status,
        notes=notes,
        reference_number=reference_number,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def create_test_invoice(
    db: Session,
    booking_id: int,
    customer_id: int = 1,
    due_date: datetime = datetime.utcnow() + timedelta(days=7),
    total_amount: Decimal = Decimal("1000000.00"),
    status: str = "pending",
    notes: Optional[str] = None,
    user_id: int = 1
) -> Invoice:
    """
    Create a test invoice
    """
    invoice = Invoice(
        invoice_number=f"INV{datetime.now().strftime('%y%m%d')}TEST",
        user_id=user_id,
        customer_id=customer_id,
        issue_date=datetime.utcnow(),
        due_date=due_date,
        status=status,
        total=total_amount,
        notes=notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def create_test_invoice_item(
    db: Session,
    invoice_id: int,
    description: str = "Test Item",
    price: Decimal = Decimal("1000000.00"),
    quantity: int = 1
) -> InvoiceItem:
    """
    Create a test invoice item
    """
    line_total = price * Decimal(quantity)
    item = InvoiceItem(
        invoice_id=invoice_id,
        package_id=1,  # Assuming package exists
        unit_price=price,
        discount=Decimal('0.00'),
        line_total=line_total,
        created_at=datetime.utcnow()
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_complete_test_booking(
    db: Session,
    user_id: int,
    customer_id: int = 1,
    villa_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a complete test booking with villa, payment, and invoice
    """
    # Create villa if not provided
    if villa_id is None:
        villa = create_test_villa(db, created_by=user_id)
        villa_id = villa.id
    
    # Create booking
    booking = create_test_booking(
        db,
        customer_id=customer_id,
        user_id=user_id
    )
    
    # Add villa to booking
    booking_villa = create_test_booking_villa(db, booking.id, villa_id)
    
    # Create invoice
    invoice = create_test_invoice(
        db,
        booking.id,
        customer_id=customer_id,
        user_id=user_id
    )
    
    # Add invoice item
    invoice_item = create_test_invoice_item(db, invoice.id)
    
    # Create payment linked to invoice
    payment = create_test_payment(
        db,
        invoice_id=invoice.id,
        user_id=user_id
    )
    
    return {
        "booking": booking,
        "villa": villa_id,
        "booking_villa": booking_villa,
        "invoice": invoice,
        "invoice_item": invoice_item,
        "payment": payment
    }