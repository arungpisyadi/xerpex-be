"""
Test utilities for the XerpeX ERP System
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking, BookingVilla, BookingPackage, BookingAddon
from app.models.payment import Payment, PaymentInvoice, PaymentInvoiceItem


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
    guest_name: str = "Test Guest",
    guest_email: str = "guest@example.com",
    guest_phone: str = "+1234567890",
    check_in: date = date.today() + timedelta(days=7),
    check_out: date = date.today() + timedelta(days=10),
    total_pax: int = 2,
    status: str = "pending",
    notes: Optional[str] = None,
    created_by: int = 1
) -> Booking:
    """
    Create a test booking
    """
    booking = Booking(
        booking_code=f"BK{datetime.now().strftime('%y%m%d')}TEST",
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        check_in=check_in,
        check_out=check_out,
        total_pax=total_pax,
        status=status,
        notes=notes,
        created_by=created_by,
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
    villa_id: int
) -> BookingVilla:
    """
    Create a test booking villa
    """
    booking_villa = BookingVilla(
        booking_id=booking_id,
        villa_id=villa_id,
        assigned_at=datetime.utcnow()
    )
    db.add(booking_villa)
    db.commit()
    db.refresh(booking_villa)
    return booking_villa


def create_test_booking_package(
    db: Session,
    booking_id: int,
    package_name: str = "Test Package",
    package_price: Decimal = Decimal("500000.00"),
    notes: Optional[str] = None
) -> BookingPackage:
    """
    Create a test booking package
    """
    booking_package = BookingPackage(
        booking_id=booking_id,
        package_name=package_name,
        package_price=package_price,
        notes=notes
    )
    db.add(booking_package)
    db.commit()
    db.refresh(booking_package)
    return booking_package


def create_test_booking_addon(
    db: Session,
    booking_id: int,
    service_name: str = "Test Addon",
    service_price: Decimal = Decimal("200000.00"),
    quantity: int = 1
) -> BookingAddon:
    """
    Create a test booking addon
    """
    booking_addon = BookingAddon(
        booking_id=booking_id,
        service_name=service_name,
        service_price=service_price,
        quantity=quantity
    )
    db.add(booking_addon)
    db.commit()
    db.refresh(booking_addon)
    return booking_addon


def create_test_payment(
    db: Session,
    booking_id: int,
    amount: Decimal = Decimal("1000000.00"),
    payment_method: str = "bank_transfer",
    payment_date: datetime = datetime.utcnow(),
    status: str = "pending",
    notes: Optional[str] = None,
    created_by: int = 1
) -> Payment:
    """
    Create a test payment
    """
    payment = Payment(
        booking_id=booking_id,
        amount=amount,
        payment_method=payment_method,
        payment_date=payment_date,
        status=status,
        notes=notes,
        created_by=created_by,
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
    guest_name: str = "Test Guest",
    guest_email: str = "guest@example.com",
    guest_phone: str = "+1234567890",
    due_date: datetime = datetime.utcnow() + timedelta(days=7),
    total_amount: Decimal = Decimal("1000000.00"),
    status: str = "pending",
    notes: Optional[str] = None,
    created_by: int = 1
) -> PaymentInvoice:
    """
    Create a test invoice
    """
    invoice = PaymentInvoice(
        invoice_number=f"INV{datetime.now().strftime('%y%m%d')}TEST",
        booking_id=booking_id,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        due_date=due_date,
        total_amount=total_amount,
        status=status,
        notes=notes,
        created_by=created_by,
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
) -> PaymentInvoiceItem:
    """
    Create a test invoice item
    """
    subtotal = price * Decimal(quantity)
    item = PaymentInvoiceItem(
        invoice_id=invoice_id,
        description=description,
        price=price,
        quantity=quantity,
        subtotal=subtotal
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def create_complete_test_booking(
    db: Session,
    user_id: int,
    villa_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a complete test booking with villa, package, addon, payment, and invoice
    """
    # Create villa if not provided
    if villa_id is None:
        villa = create_test_villa(db, created_by=user_id)
        villa_id = villa.id
    
    # Create booking
    booking = create_test_booking(
        db,
        guest_name="Complete Test Guest",
        created_by=user_id
    )
    
    # Add villa to booking
    booking_villa = create_test_booking_villa(db, booking.id, villa_id)
    
    # Add package to booking
    booking_package = create_test_booking_package(db, booking.id)
    
    # Add addon to booking
    booking_addon = create_test_booking_addon(db, booking.id)
    
    # Create invoice
    invoice = create_test_invoice(
        db,
        booking.id,
        guest_name="Complete Test Guest",
        created_by=user_id
    )
    
    # Add invoice item
    invoice_item = create_test_invoice_item(db, invoice.id)
    
    # Create payment
    payment = create_test_payment(
        db,
        booking.id,
        created_by=user_id
    )
    
    # Link payment to invoice
    payment.invoice_id = invoice.id
    db.commit()
    db.refresh(payment)
    
    return {
        "booking": booking,
        "villa": villa_id,
        "booking_villa": booking_villa,
        "booking_package": booking_package,
        "booking_addon": booking_addon,
        "invoice": invoice,
        "invoice_item": invoice_item,
        "payment": payment
    }