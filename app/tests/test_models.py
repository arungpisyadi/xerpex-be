"""
Tests for database models
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking, BookingVilla
from app.models.payment import Payment, Invoice, InvoiceItem
from app.tests.utils import (
    create_test_villa, create_test_villa_availability,
    create_test_booking, create_test_booking_villa,
    create_test_payment, create_test_invoice,
    create_test_invoice_item, create_complete_test_booking
)


def test_user_model(db: Session):
    """Test User model"""
    # Create user
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashedpassword",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Check user attributes
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.hashed_password == "hashedpassword"
    assert user.is_active is True
    assert user.is_admin is False
    assert user.created_at is not None
    assert user.updated_at is not None


def test_villa_model(db: Session):
    """Test Villa model"""
    # Create villa
    villa = create_test_villa(db)
    
    # Check villa attributes
    assert villa.id is not None
    assert villa.name == "Test Villa"
    assert villa.description == "Test villa description"
    assert villa.base_price == Decimal("1000000.00")
    assert villa.max_guests == 4
    assert villa.bedrooms == 2
    assert villa.bathrooms == 2
    assert villa.created_by == 1
    assert villa.created_at is not None
    assert villa.updated_at is not None


def test_villa_availability_model(db: Session):
    """Test VillaAvailability model"""
    # Create villa
    villa = create_test_villa(db)
    
    # Create villa availability
    today = date.today()
    availability = create_test_villa_availability(db, villa.id, today)
    
    # Check availability attributes
    assert availability.id is not None
    assert availability.villa_id == villa.id
    assert availability.date == today
    assert availability.is_available is True
    assert availability.blocked_reason is None
    assert availability.updated_by == 1
    assert availability.updated_at is not None


def test_booking_model(db: Session):
    """Test Booking model"""
    # Create booking
    booking = create_test_booking(db)
    
    # Check booking attributes
    assert booking.id is not None
    assert booking.booking_code is not None
    assert booking.guest_name == "Test Guest"
    assert booking.guest_email == "guest@example.com"
    assert booking.guest_phone == "+1234567890"
    assert booking.check_in == date.today() + timedelta(days=7)
    assert booking.check_out == date.today() + timedelta(days=10)
    assert booking.total_pax == 2
    assert booking.status == "pending"
    assert booking.notes is None
    assert booking.created_by == 1
    assert booking.created_at is not None
    assert booking.updated_at is not None


def test_booking_villa_model(db: Session):
    """Test BookingVilla model (simplified junction table)"""
    # Create villa and booking
    villa = create_test_villa(db)
    booking = create_test_booking(db)
    
    # Create booking villa
    booking_villa = create_test_booking_villa(db, booking.id, villa.id)
    
    # Check booking villa attributes
    assert booking_villa.id is not None
    assert booking_villa.booking_id == booking.id
    assert booking_villa.villa_id == villa.id
    assert booking_villa.created_at is not None


def test_payment_model(db: Session):
    """Test Payment model"""
    # Create booking and invoice
    booking = create_test_booking(db)
    invoice = create_test_invoice(db, booking.id)
    
    # Create payment
    payment = create_test_payment(db, invoice_id=invoice.id)
    
    # Check payment attributes
    assert payment.id is not None
    assert payment.invoice_id == invoice.id
    assert payment.amount == Decimal("1000000.00")
    assert payment.payment_method == "bank_transfer"
    assert payment.payment_date is not None
    assert payment.status == "pending"
    assert payment.notes is None
    assert payment.user_id == 1
    assert payment.created_at is not None
    assert payment.updated_at is not None


def test_invoice_model(db: Session):
    """Test Invoice model"""
    # Create booking
    booking = create_test_booking(db)
    
    # Create invoice
    invoice = create_test_invoice(db, booking.id)
    
    # Check invoice attributes
    assert invoice.id is not None
    assert invoice.invoice_number is not None
    assert invoice.customer_id == 1
    assert invoice.due_date is not None
    assert invoice.total == Decimal("1000000.00")
    assert invoice.status == "pending"
    assert invoice.notes is None
    assert invoice.user_id == 1
    assert invoice.created_at is not None
    assert invoice.updated_at is not None


def test_invoice_item_model(db: Session):
    """Test InvoiceItem model"""
    # Create booking and invoice
    booking = create_test_booking(db)
    invoice = create_test_invoice(db, booking.id)
    
    # Create invoice item
    item = create_test_invoice_item(db, invoice.id)
    
    # Check invoice item attributes
    assert item.id is not None
    assert item.invoice_id == invoice.id
    assert item.unit_price == Decimal("1000000.00")
    assert item.line_total == Decimal("1000000.00")


def test_model_relationships(db: Session):
    """Test model relationships"""
    # Create test user
    user = User(
        username="relationuser",
        email="relation@example.com",
        full_name="Relation User",
        hashed_password="hashedpassword",
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create complete booking
    test_data = create_complete_test_booking(db, user.id)
    
    # Test booking to villa relationship
    booking = test_data["booking"]
    booking_villa = test_data["booking_villa"]
    
    assert len(booking.villas) == 1
    assert booking.villas[0].id == booking_villa.id
    assert booking.villas[0].villa_id == test_data["villa"]
    
    # Test invoice to items relationship
    invoice = test_data["invoice"]
    assert len(invoice.items) == 1
    assert invoice.items[0].id == test_data["invoice_item"].id
    
    # Test invoice to payments relationship
    assert len(invoice.payments) == 1
    assert invoice.payments[0].id == test_data["payment"].id
    assert invoice.payments[0].amount == Decimal("1000000.00")
    
    # Test payment to invoice relationship
    payment = test_data["payment"]
    assert payment.invoice_id == invoice.id
    assert payment.invoice.id == invoice.id