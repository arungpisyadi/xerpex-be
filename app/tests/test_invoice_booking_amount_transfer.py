"""
Unit tests for invoice-to-booking conversion amount transfer functionality

This test suite specifically verifies that amount_paid and amount_due are correctly
preserved when converting invoices to bookings, covering:
- Unpaid invoices (amount_paid=0)
- Partially paid invoices
- Fully paid invoices
- Overpaid invoices

Test Credentials:
- username: admin@tugugroup.co.id
- password: 1q2w3e4r5t

Context:
Bug fix in app/services/payment.py:1324-1325 now correctly transfers amount_paid
and amount_due from invoices to bookings during conversion.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.payment import Invoice, InvoiceItem, InvoiceVilla
from app.models.booking import Booking
from app.schemas.payment import InvoiceToBookingRequest
from app.services.payment import convert_invoice_to_booking


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing"""
    user = User(
        username="admin_amount_transfer",
        email="admin@tugugroup.co.id",
        full_name="Admin User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='admin'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_customer(db: Session, admin_user: User) -> Customer:
    """Create a test customer"""
    customer = Customer(
        user_id=admin_user.id,
        name="Test Customer Amount Transfer",
        email="amount_transfer@test.com",
        phone_number="6281234567890",
        address="Test Address",
        billing_address="Test Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_package(db: Session, admin_user: User) -> Package:
    """Create a test package"""
    package = Package(
        user_id=admin_user.id,
        name="Test Package Amount Transfer",
        category="Adventure",
        type="Tour",
        description="Test package for amount transfer",
        days=3,
        cost_per_pax=Decimal("1000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@pytest.fixture
def test_villa(db: Session) -> Villa:
    """Create a test villa"""
    villa = Villa(
        name="Test Villa Amount Transfer",
        description="Test villa for amount transfer",
        capacity="4",
        room_type="Standard",
        base_price=Decimal("0.00"),  # Set to 0 to simplify total calculations
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


def create_invoice_with_amounts(
    db: Session,
    user: User,
    customer: Customer,
    package: Package,
    villa: Villa,
    status: str,
    total: Decimal,
    amount_paid: Decimal,
    amount_due: Decimal
) -> Invoice:
    """Helper function to create an invoice with specific payment amounts"""
    invoice = Invoice(
        user_id=user.id,
        customer_id=customer.id,
        invoice_number=f"INV-AMT-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status=status,
        total=total,
        amount_paid=amount_paid,
        amount_due=amount_due,
        tax_total=Decimal("0.00"),
        payment_terms="Due on receipt",
        notes="Test invoice for amount transfer",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal("1000.00"),
        discount=Decimal("0.00"),
        pax=100,
        line_total=total,  # Use total directly for simplicity
        created_at=datetime.utcnow()
    )
    db.add(item)
    
    # Add invoice villa
    invoice_villa = InvoiceVilla(
        invoice_id=invoice.id,
        villa_id=villa.id
    )
    db.add(invoice_villa)
    
    db.commit()
    db.refresh(invoice)
    return invoice


# ============================================================================
# Test Cases
# ============================================================================

class TestInvoiceBookingAmountTransfer:
    """Test suite for verifying amount_paid and amount_due transfer during conversion"""
    
    def test_convert_unpaid_invoice(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """
        Test Case 1: Convert unpaid invoice (amount_paid=0)
        Invoice: total=100, amount_paid=0, amount_due=100
        Expected Booking: total=100, amount_paid=0, amount_due=100
        """
        # Create unpaid invoice
        total = Decimal("100.00")
        amount_paid = Decimal("0.00")
        amount_due = Decimal("100.00")
        
        invoice = create_invoice_with_amounts(
            db=db,
            user=admin_user,
            customer=test_customer,
            package=test_package,
            villa=test_villa,
            status="partially_paid",
            total=total,
            amount_paid=amount_paid,
            amount_due=amount_due
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Test unpaid invoice conversion"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        
        # Verify amount_paid and amount_due are preserved
        assert booking.total == total
        assert booking.amount_paid == amount_paid  # Should be 0
        assert booking.amount_due == amount_due    # Should be 100
        
        # Verify they match the original invoice values
        assert booking.amount_paid == invoice.amount_paid
        assert booking.amount_due == invoice.amount_due
    
    def test_convert_partially_paid_invoice(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """
        Test Case 2: Convert partially_paid invoice
        Invoice: total=100, amount_paid=30, amount_due=70
        Expected Booking: total=100, amount_paid=30, amount_due=70
        """
        # Create partially paid invoice
        total = Decimal("100.00")
        amount_paid = Decimal("30.00")
        amount_due = Decimal("70.00")
        
        invoice = create_invoice_with_amounts(
            db=db,
            user=admin_user,
            customer=test_customer,
            package=test_package,
            villa=test_villa,
            status="partially_paid",
            total=total,
            amount_paid=amount_paid,
            amount_due=amount_due
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Test partially paid invoice conversion"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        
        # Verify amount_paid and amount_due are preserved
        assert booking.total == total
        assert booking.amount_paid == amount_paid  # Should be 30
        assert booking.amount_due == amount_due    # Should be 70
        
        # Verify they match the original invoice values
        assert booking.amount_paid == invoice.amount_paid
        assert booking.amount_due == invoice.amount_due
        
        # Verify the math is correct
        assert booking.amount_paid + booking.amount_due == booking.total
    
    def test_convert_fully_paid_invoice(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """
        Test Case 3: Convert paid invoice
        Invoice: total=100, amount_paid=100, amount_due=0
        Expected Booking: total=100, amount_paid=100, amount_due=0
        """
        # Create fully paid invoice
        total = Decimal("100.00")
        amount_paid = Decimal("100.00")
        amount_due = Decimal("0.00")
        
        invoice = create_invoice_with_amounts(
            db=db,
            user=admin_user,
            customer=test_customer,
            package=test_package,
            villa=test_villa,
            status="paid",
            total=total,
            amount_paid=amount_paid,
            amount_due=amount_due
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Test fully paid invoice conversion"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        
        # Verify amount_paid and amount_due are preserved
        assert booking.total == total
        assert booking.amount_paid == amount_paid  # Should be 100
        assert booking.amount_due == amount_due    # Should be 0
        
        # Verify they match the original invoice values
        assert booking.amount_paid == invoice.amount_paid
        assert booking.amount_due == invoice.amount_due
        
        # Verify the booking is fully paid
        assert booking.amount_paid == booking.total
        assert booking.amount_due == Decimal("0.00")
    
    def test_convert_overpaid_invoice(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """
        Test Case 4: Convert invoice with overpayment (if applicable)
        Invoice: total=100, amount_paid=120, amount_due=-20
        Expected Booking: total=100, amount_paid=120, amount_due=-20
        """
        # Create overpaid invoice
        total = Decimal("100.00")
        amount_paid = Decimal("120.00")
        amount_due = Decimal("-20.00")
        
        invoice = create_invoice_with_amounts(
            db=db,
            user=admin_user,
            customer=test_customer,
            package=test_package,
            villa=test_villa,
            status="paid",
            total=total,
            amount_paid=amount_paid,
            amount_due=amount_due
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Test overpaid invoice conversion"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        
        # Verify amount_paid and amount_due are preserved (including negative amount_due)
        assert booking.total == total
        assert booking.amount_paid == amount_paid  # Should be 120
        assert booking.amount_due == amount_due    # Should be -20
        
        # Verify they match the original invoice values
        assert booking.amount_paid == invoice.amount_paid
        assert booking.amount_due == invoice.amount_due
        
        # Verify overpayment is preserved
        assert booking.amount_paid > booking.total
        assert booking.amount_due < Decimal("0.00")
        assert booking.amount_paid - booking.total == Decimal("20.00")
    
    def test_amount_transfer_with_different_totals(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """
        Additional test: Verify amount transfer works correctly with various total amounts
        This ensures the fix works regardless of the invoice total
        """
        test_cases = [
            # (total, amount_paid, amount_due, status)
            (Decimal("50.00"), Decimal("0.00"), Decimal("50.00"), "partially_paid"),
            (Decimal("200.00"), Decimal("100.00"), Decimal("100.00"), "partially_paid"),
            (Decimal("500.00"), Decimal("500.00"), Decimal("0.00"), "paid"),
            (Decimal("75.50"), Decimal("25.50"), Decimal("50.00"), "partially_paid"),
        ]
        
        for total, amount_paid, amount_due, status in test_cases:
            # Create invoice with specific amounts
            invoice = create_invoice_with_amounts(
                db=db,
                user=admin_user,
                customer=test_customer,
                package=test_package,
                villa=test_villa,
                status=status,
                total=total,
                amount_paid=amount_paid,
                amount_due=amount_due
            )
            
            # Prepare conversion request
            request_data = InvoiceToBookingRequest(
                invoice_id=invoice.id,
                check_in=date.today() + timedelta(days=5),
                check_out=date.today() + timedelta(days=8),
                total_pax=4,
                notes=f"Test conversion with total={total}"
            )
            
            # Convert to booking
            result = convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
            
            # Verify booking was created with correct amounts
            booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
            assert booking is not None
            assert booking.total == total, f"Failed for total={total}"
            assert booking.amount_paid == amount_paid, f"Failed for amount_paid={amount_paid}"
            assert booking.amount_due == amount_due, f"Failed for amount_due={amount_due}"
            
            # Verify amounts match the invoice
            assert booking.amount_paid == invoice.amount_paid
            assert booking.amount_due == invoice.amount_due