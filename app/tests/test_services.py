"""
Tests for service functions
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.villa import Villa
from app.models.booking import Booking
from app.models.payment import Payment, PaymentInvoice
from app.schemas.user import UserCreate
from app.schemas.villa import VillaCreate, VillaAvailabilityCreate
from app.schemas.booking import BookingCreate, BookingVillaCreate, BookingStatusUpdate
from app.schemas.payment import PaymentCreate, PaymentStatusUpdate
from app.services.auth import authenticate_user, create_user, get_current_user
from app.services.user import get_user, get_user_by_email, get_users
from app.services.villa import (
    get_villa, get_villas, create_villa, update_villa,
    check_villa_availability, create_villa_availability
)
from app.services.booking import (
    get_booking, get_bookings, create_booking, update_booking_status,
    get_booking_details
)
from app.services.payment import (
    get_payment, get_payments, create_payment, update_payment_status,
    get_invoice, create_invoice, get_booking_payment_summary
)
from app.services.report import (
    get_villa_occupancy_report, get_booking_status_report,
    get_revenue_report, get_dashboard_summary
)
from app.tests.utils import (
    create_test_villa, create_test_booking, create_test_payment,
    create_test_invoice, create_complete_test_booking
)


# Auth service tests
def test_create_user(db: Session):
    """Test create_user service"""
    user_data = UserCreate(
        username="serviceuser",
        email="service@example.com",
        full_name="Service User",
        password="password123"
    )
    
    user = create_user(db, user_data)
    
    assert user.id is not None
    assert user.username == "serviceuser"
    assert user.email == "service@example.com"
    assert user.full_name == "Service User"
    assert user.hashed_password != "password123"  # Password should be hashed
    assert user.is_active is True
    assert user.is_admin is False


def test_authenticate_user(db: Session):
    """Test authenticate_user service"""
    # Create user
    user_data = UserCreate(
        username="authuser",
        email="auth@example.com",
        full_name="Auth User",
        password="password123"
    )
    
    create_user(db, user_data)
    
    # Test successful authentication
    user = authenticate_user(db, "authuser", "password123")
    assert user is not None
    assert user.username == "authuser"
    
    # Test failed authentication - wrong password
    user = authenticate_user(db, "authuser", "wrongpassword")
    assert user is None
    
    # Test failed authentication - user doesn't exist
    user = authenticate_user(db, "nonexistentuser", "password123")
    assert user is None


def test_get_current_user(db: Session):
    """Test get_current_user service"""
    # Create user
    user_data = UserCreate(
        username="currentuser",
        email="current@example.com",
        full_name="Current User",
        password="password123"
    )
    
    created_user = create_user(db, user_data)
    
    # Test get current user
    user = get_current_user(db, "currentuser")
    assert user is not None
    assert user.id == created_user.id
    assert user.username == "currentuser"
    
    # Test get current user - user doesn't exist
    user = get_current_user(db, "nonexistentuser")
    assert user is None


# User service tests
def test_get_user(db: Session, test_user):
    """Test get_user service"""
    user = get_user(db, test_user["id"])
    assert user is not None
    assert user.id == test_user["id"]
    assert user.username == test_user["username"]
    
    # Test get user - user doesn't exist
    user = get_user(db, 9999)
    assert user is None


def test_get_user_by_email(db: Session, test_user):
    """Test get_user_by_email service"""
    user = get_user_by_email(db, test_user["email"])
    assert user is not None
    assert user.id == test_user["id"]
    assert user.email == test_user["email"]
    
    # Test get user by email - user doesn't exist
    user = get_user_by_email(db, "nonexistent@example.com")
    assert user is None


def test_get_users(db: Session, test_user, test_admin):
    """Test get_users service"""
    users = get_users(db)
    assert len(users) >= 2  # At least test_user and test_admin
    
    # Check if test_user and test_admin are in the results
    user_ids = [user.id for user in users]
    assert test_user["id"] in user_ids
    assert test_admin["id"] in user_ids


# Villa service tests
def test_create_villa(db: Session, test_user):
    """Test create_villa service"""
    villa_data = VillaCreate(
        name="Service Villa",
        description="Villa created by service test",
        base_price=Decimal("1500000.00"),
        max_guests=6,
        bedrooms=3,
        bathrooms=3
    )
    
    villa = create_villa(db, villa_data, test_user["id"])
    
    assert villa.id is not None
    assert villa.name == "Service Villa"
    assert villa.description == "Villa created by service test"
    assert villa.base_price == Decimal("1500000.00")
    assert villa.max_guests == 6
    assert villa.bedrooms == 3
    assert villa.bathrooms == 3
    assert villa.created_by == test_user["id"]


def test_get_villa(db: Session):
    """Test get_villa service"""
    # Create villa
    villa = create_test_villa(db)
    
    # Test get villa
    retrieved_villa = get_villa(db, villa.id)
    assert retrieved_villa is not None
    assert retrieved_villa.id == villa.id
    assert retrieved_villa.name == villa.name
    
    # Test get villa - villa doesn't exist
    retrieved_villa = get_villa(db, 9999)
    assert retrieved_villa is None


def test_get_villas(db: Session):
    """Test get_villas service"""
    # Create villas
    villa1 = create_test_villa(db, name="Test Villa 1")
    villa2 = create_test_villa(db, name="Test Villa 2")
    
    # Test get villas
    villas = get_villas(db)
    assert len(villas) >= 2  # At least the two we created
    
    # Check if our villas are in the results
    villa_ids = [v.id for v in villas]
    assert villa1.id in villa_ids
    assert villa2.id in villa_ids


def test_check_villa_availability(db: Session):
    """Test check_villa_availability service"""
    # Create villa
    villa = create_test_villa(db)
    
    # Test availability when no bookings exist
    today = date.today()
    tomorrow = today + timedelta(days=1)
    is_available, _ = check_villa_availability(db, villa.id, today, tomorrow)
    assert is_available is True
    
    # Create booking for the villa
    booking = create_test_booking(
        db,
        check_in=today,
        check_out=tomorrow
    )
    create_test_booking_villa(db, booking.id, villa.id)
    
    # Test availability when booking exists
    is_available, _ = check_villa_availability(db, villa.id, today, tomorrow)
    assert is_available is False


def test_create_villa_availability(db: Session, test_user):
    """Test create_villa_availability service"""
    # Create villa
    villa = create_test_villa(db)
    
    # Create availability
    today = date.today()
    availability_data = VillaAvailabilityCreate(
        villa_id=villa.id,
        date=today,
        is_available=False,
        blocked_reason="Maintenance"
    )
    
    availability = create_villa_availability(db, availability_data, test_user["id"])
    
    assert availability.id is not None
    assert availability.villa_id == villa.id
    assert availability.date == today
    assert availability.is_available is False
    assert availability.blocked_reason == "Maintenance"
    assert availability.updated_by == test_user["id"]


# Booking service tests
def test_create_booking(db: Session, test_user):
    """Test create_booking service"""
    # Create villa
    villa = create_test_villa(db)
    
    # Create booking data
    today = date.today()
    tomorrow = today + timedelta(days=1)
    booking_data = BookingCreate(
        guest_name="Service Booking Guest",
        guest_email="booking@example.com",
        guest_phone="+1234567890",
        check_in=today,
        check_out=tomorrow,
        total_pax=2,
        notes="Service booking test",
        villas=[BookingVillaCreate(villa_id=villa.id)],
        packages=[],
        addons=[]
    )
    
    booking = create_booking(db, booking_data, test_user["id"])
    
    assert booking.id is not None
    assert booking.booking_code is not None
    assert booking.guest_name == "Service Booking Guest"
    assert booking.guest_email == "booking@example.com"
    assert booking.check_in == today
    assert booking.check_out == tomorrow
    assert booking.status == "pending"
    assert booking.created_by == test_user["id"]
    assert len(booking.villas) == 1
    assert booking.villas[0].villa_id == villa.id


def test_get_booking(db: Session):
    """Test get_booking service"""
    # Create booking
    booking = create_test_booking(db)
    
    # Test get booking
    retrieved_booking = get_booking(db, booking.id)
    assert retrieved_booking is not None
    assert retrieved_booking.id == booking.id
    assert retrieved_booking.booking_code == booking.booking_code
    
    # Test get booking - booking doesn't exist
    retrieved_booking = get_booking(db, 9999)
    assert retrieved_booking is None


def test_get_bookings(db: Session):
    """Test get_bookings service"""
    # Create bookings
    booking1 = create_test_booking(db, guest_name="Test Booking 1")
    booking2 = create_test_booking(db, guest_name="Test Booking 2")
    
    # Test get bookings
    bookings = get_bookings(db)
    assert len(bookings) >= 2  # At least the two we created
    
    # Check if our bookings are in the results
    booking_ids = [b.id for b in bookings]
    assert booking1.id in booking_ids
    assert booking2.id in booking_ids
    
    # Test filtering by guest name
    filtered_bookings = get_bookings(db, guest_name="Booking 1")
    assert len(filtered_bookings) >= 1
    assert any(b.guest_name == "Test Booking 1" for b in filtered_bookings)
    assert not any(b.guest_name == "Test Booking 2" for b in filtered_bookings)


def test_update_booking_status(db: Session):
    """Test update_booking_status service"""
    # Create booking
    booking = create_test_booking(db)
    assert booking.status == "pending"
    
    # Update status to confirmed
    status_update = BookingStatusUpdate(status="confirmed")
    updated_booking = update_booking_status(db, booking.id, status_update)
    
    assert updated_booking.id == booking.id
    assert updated_booking.status == "confirmed"


def test_get_booking_details(db: Session, test_user):
    """Test get_booking_details service"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    booking = test_data["booking"]
    
    # Get booking details
    details = get_booking_details(db, booking.id)
    
    assert details["booking"].id == booking.id
    assert "total_price" in details
    assert "total_paid" in details
    assert "balance" in details


# Payment service tests
def test_create_payment(db: Session, test_user):
    """Test create_payment service"""
    # Create booking
    booking = create_test_booking(db)
    
    # Create payment data
    payment_data = PaymentCreate(
        booking_id=booking.id,
        amount=Decimal("1000000.00"),
        payment_method="credit_card",
        payment_date=datetime.utcnow(),
        notes="Service payment test"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    assert payment.id is not None
    assert payment.booking_id == booking.id
    assert payment.amount == Decimal("1000000.00")
    assert payment.payment_method == "credit_card"
    assert payment.status == "pending"
    assert payment.notes == "Service payment test"
    assert payment.created_by == test_user["id"]


def test_get_payment(db: Session):
    """Test get_payment service"""
    # Create booking and payment
    booking = create_test_booking(db)
    payment = create_test_payment(db, booking.id)
    
    # Test get payment
    retrieved_payment = get_payment(db, payment.id)
    assert retrieved_payment is not None
    assert retrieved_payment.id == payment.id
    assert retrieved_payment.booking_id == booking.id
    
    # Test get payment - payment doesn't exist
    retrieved_payment = get_payment(db, 9999)
    assert retrieved_payment is None


def test_get_payments(db: Session):
    """Test get_payments service"""
    # Create bookings and payments
    booking1 = create_test_booking(db, guest_name="Payment Test 1")
    booking2 = create_test_booking(db, guest_name="Payment Test 2")
    payment1 = create_test_payment(db, booking1.id, payment_method="bank_transfer")
    payment2 = create_test_payment(db, booking2.id, payment_method="credit_card")
    
    # Test get payments
    payments = get_payments(db)
    assert len(payments) >= 2  # At least the two we created
    
    # Check if our payments are in the results
    payment_ids = [p.id for p in payments]
    assert payment1.id in payment_ids
    assert payment2.id in payment_ids
    
    # Test filtering by payment method
    filtered_payments = get_payments(db, payment_method="bank_transfer")
    assert len(filtered_payments) >= 1
    assert any(p.payment_method == "bank_transfer" for p in filtered_payments)
    assert not any(p.payment_method == "credit_card" for p in filtered_payments)


def test_update_payment_status(db: Session):
    """Test update_payment_status service"""
    # Create booking and payment
    booking = create_test_booking(db)
    payment = create_test_payment(db, booking.id)
    assert payment.status == "pending"
    
    # Update status to paid
    status_update = PaymentStatusUpdate(status="paid")
    updated_payment = update_payment_status(db, payment.id, status_update)
    
    assert updated_payment.id == payment.id
    assert updated_payment.status == "paid"


def test_create_invoice(db: Session, test_user):
    """Test create_invoice service"""
    # Create booking
    booking = create_test_booking(db)
    
    # Create invoice data
    from app.schemas.payment import PaymentInvoiceCreate
    invoice_data = PaymentInvoiceCreate(
        booking_id=booking.id,
        guest_name=booking.guest_name,
        guest_email=booking.guest_email,
        guest_phone=booking.guest_phone,
        due_date=datetime.utcnow() + timedelta(days=7),
        items=[
            {
                "description": "Villa Stay",
                "price": 1000000,
                "quantity": 1
            }
        ],
        notes="Service invoice test"
    )
    
    invoice = create_invoice(db, invoice_data, test_user["id"])
    
    assert invoice.id is not None
    assert invoice.booking_id == booking.id
    assert invoice.invoice_number is not None
    assert invoice.guest_name == booking.guest_name
    assert invoice.total_amount == Decimal("1000000.00")
    assert invoice.status == "pending"
    assert invoice.notes == "Service invoice test"
    assert invoice.created_by == test_user["id"]
    assert len(invoice.items) == 1
    assert invoice.items[0].description == "Villa Stay"


def test_get_invoice(db: Session):
    """Test get_invoice service"""
    # Create booking and invoice
    booking = create_test_booking(db)
    invoice = create_test_invoice(db, booking.id)
    
    # Test get invoice
    retrieved_invoice = get_invoice(db, invoice.id)
    assert retrieved_invoice is not None
    assert retrieved_invoice.id == invoice.id
    assert retrieved_invoice.booking_id == booking.id
    
    # Test get invoice - invoice doesn't exist
    retrieved_invoice = get_invoice(db, 9999)
    assert retrieved_invoice is None


def test_get_booking_payment_summary(db: Session, test_user):
    """Test get_booking_payment_summary service"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    booking = test_data["booking"]
    
    # Get payment summary
    summary = get_booking_payment_summary(db, booking.id)
    
    assert summary["booking_id"] == booking.id
    assert summary["booking_code"] == booking.booking_code
    assert summary["guest_name"] == booking.guest_name
    assert "total_invoiced" in summary
    assert "total_paid" in summary
    assert "balance" in summary
    assert "payments" in summary
    assert "invoices" in summary


# Report service tests
def test_get_villa_occupancy_report(db: Session, test_user):
    """Test get_villa_occupancy_report service"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    
    # Create report parameters
    from app.schemas.report import ReportVillaOccupancyParams
    params = ReportVillaOccupancyParams(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=30),
        villa_id=None  # All villas
    )
    
    # Get report
    report = get_villa_occupancy_report(db, params)
    
    assert "start_date" in report
    assert "end_date" in report
    assert "total_days" in report
    assert "villas" in report
    assert "average_occupancy_rate" in report
    assert "total_revenue" in report
    assert len(report["villas"]) > 0


def test_get_booking_status_report(db: Session, test_user):
    """Test get_booking_status_report service"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    
    # Create report parameters
    from app.schemas.report import ReportBookingStatusParams
    params = ReportBookingStatusParams(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=30),
        status=None  # All statuses
    )
    
    # Get report
    report = get_booking_status_report(db, params)
    
    assert "start_date" in report
    assert "end_date" in report
    assert "total_bookings" in report
    assert "status_breakdown" in report
    assert len(report["status_breakdown"]) > 0


def test_get_revenue_report(db: Session, test_user):
    """Test get_revenue_report service"""
    # Create complete booking with paid payment
    test_data = create_complete_test_booking(db, test_user["id"])
    payment = test_data["payment"]
    payment.status = "paid"
    
    # Create report parameters
    from app.schemas.report import ReportRevenueParams
    params = ReportRevenueParams(
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=30),
        group_by="day"
    )
    
    # Get report
    report = get_revenue_report(db, params)
    
    assert "start_date" in report
    assert "end_date" in report
    assert "group_by" in report
    assert "total_revenue" in report
    assert "total_bookings" in report
    assert "average_booking_value" in report
    assert "items" in report


def test_get_dashboard_summary(db: Session, test_user):
    """Test get_dashboard_summary service"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    
    # Get dashboard summary
    summary = get_dashboard_summary(db)
    
    assert "total_bookings" in summary
    assert "pending_bookings" in summary
    assert "ongoing_bookings" in summary
    assert "completed_bookings" in summary
    assert "cancelled_bookings" in summary
    assert "total_revenue" in summary
    assert "pending_payments" in summary
    assert "occupancy_rate" in summary
    assert "top_villas" in summary
    assert "recent_bookings" in summary
    assert "revenue_chart" in summary