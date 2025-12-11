"""
Comprehensive tests for invoice-to-booking conversion endpoint

This test suite verifies the invoice-to-booking conversion functionality including:
- Successful conversions with valid statuses (partially_paid, paid)
- Status validation (only partially_paid and paid allowed)
- Duplicate conversion prevention
- Date validation (check_out > check_in)
- Invoice not found handling
- Role-based access control
- Data integrity (correct field mapping)
- Items and villas copying
- History event recording for both invoice and booking

Test Credentials:
- username: admin@tugugroup.co.id
- password: 1q2w3e4r5t
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException
from pydantic_core import ValidationError

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.payment import Invoice, InvoiceItem, InvoiceVilla, InvoiceHistory
from app.models.booking import Booking, BookingItem, BookingVilla, BookingHistory
from app.schemas.payment import InvoiceToBookingRequest, InvoiceStatus
from app.services.payment import convert_invoice_to_booking


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing"""
    user = User(
        username="admin_booking_convert",
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
def finance_user(db: Session) -> User:
    """Create a finance user for testing"""
    user = User(
        username="finance_booking_convert",
        email="finance@tugugroup.co.id",
        full_name="Finance User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='finance'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sales_user(db: Session) -> User:
    """Create a sales user for testing"""
    user = User(
        username="sales_booking_convert",
        email="sales@tugugroup.co.id",
        full_name="Sales User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='sales'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db: Session) -> User:
    """Create a regular user for testing"""
    user = User(
        username="regular_booking_convert",
        email="regular@tugugroup.co.id",
        full_name="Regular User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_customer(db: Session, regular_user: User) -> Customer:
    """Create a test customer"""
    customer = Customer(
        user_id=regular_user.id,
        name="Test Customer for Booking",
        email="booking_customer@test.com",
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
def test_package(db: Session, regular_user: User) -> Package:
    """Create a test package"""
    package = Package(
        user_id=regular_user.id,
        name="Test Package for Booking Conversion",
        category="Adventure",
        type="Tour",
        description="Test package",
        days=3,
        cost_per_pax=Decimal("500000.00"),
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
        name="Test Villa for Booking",
        description="Test villa",
        capacity="4",
        room_type="Deluxe",
        base_price=Decimal("2000000.00"),
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


def create_test_invoice(
    db: Session,
    user: User,
    customer: Customer,
    package: Package,
    villa: Villa,
    status: str = "partially_paid",
    total: Decimal = Decimal("52000000.00"),
    amount_paid: Decimal = Decimal("0.00")
) -> Invoice:
    """Helper function to create a test invoice with items and villas"""
    invoice = Invoice(
        user_id=user.id,
        customer_id=customer.id,
        invoice_number=f"INV-TEST-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status=status,
        total=total,
        amount_paid=amount_paid,
        amount_due=total - amount_paid,
        tax_total=Decimal("0.00"),
        payment_terms="Due on receipt",
        notes="Test invoice for conversion",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal("500000.00"),
        discount=Decimal("0.00"),
        pax=100,
        line_total=Decimal("50000000.00"),
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
# Test Classes
# ============================================================================

class TestInvoiceToBookingConversion:
    """Test suite for invoice-to-booking conversion endpoint"""
    
    def test_successful_conversion_partially_paid(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test successful conversion of partially_paid invoice"""
        # Create partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted from partially paid invoice"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Assert result structure
        assert result is not None
        assert "booking_id" in result
        assert "booking_code" in result
        assert "invoice_id" in result
        assert result["invoice_id"] == invoice.id
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        assert booking.booking_code == result["booking_code"]
        assert booking.customer_id == invoice.customer_id
        assert booking.user_id == invoice.user_id
        assert booking.status == "pending"
        assert booking.total == invoice.total
        assert booking.amount_paid == invoice.amount_paid  # Preserves payment from invoice
        assert booking.amount_due == invoice.amount_due    # Preserves remaining balance from invoice
    
    def test_successful_conversion_paid(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test successful conversion of paid invoice"""
        # Create paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="paid"
        )
        
        # Prepare conversion request
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted from paid invoice"
        )
        
        # Convert to booking
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Assert conversion succeeded
        assert result is not None
        assert "booking_id" in result
        assert result["invoice_id"] == invoice.id
        
        # Verify booking exists
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        assert booking.status == "pending"
    
    def test_conversion_invalid_status_sent(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails for sent status"""
        # Create sent invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="sent"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # Should raise HTTPException with 400
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
        assert "partially_paid" in exc_info.value.detail.lower() or "paid" in exc_info.value.detail.lower()
    
    def test_conversion_invalid_status_draft(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails for draft status"""
        # Create draft invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="draft"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
    
    def test_conversion_invalid_status_overdue(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails for overdue status"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="overdue"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
    
    def test_conversion_invalid_status_cancelled(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails for cancelled status"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="cancelled"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
    
    def test_conversion_duplicate_prevention(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test duplicate conversion is prevented"""
        # Create partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # First conversion should succeed
        result1 = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        assert result1 is not None
        
        # Verify booking was created
        booking = db.query(Booking).filter(Booking.id == result1["booking_id"]).first()
        assert booking is not None
        
        # Link invoice to booking for duplicate check by updating invoice's booking_id
        invoice.booking_id = booking.id
        db.commit()
        
        # Second conversion should now fail
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
        assert "already been converted" in exc_info.value.detail.lower()
    
    def test_conversion_invalid_dates_equal(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails with check_out equal to check_in"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        same_date = date.today() + timedelta(days=5)
        
        # Pydantic validates dates before service function is called
        with pytest.raises(ValidationError) as exc_info:
            request_data = InvoiceToBookingRequest(
                invoice_id=invoice.id,
                check_in=same_date,
                check_out=same_date,  # Same as check_in
                total_pax=4
            )
        
        # Verify the validation error is for check_out
        assert "check_out" in str(exc_info.value).lower()
    
    def test_conversion_invalid_dates_before(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion fails with check_out before check_in"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        # Pydantic validates dates before service function is called
        with pytest.raises(ValidationError) as exc_info:
            request_data = InvoiceToBookingRequest(
                invoice_id=invoice.id,
                check_in=date.today() + timedelta(days=8),
                check_out=date.today() + timedelta(days=5),  # Before check_in
                total_pax=4
            )
        
        # Verify the validation error is for check_out
        assert "check_out" in str(exc_info.value).lower()
    
    def test_conversion_valid_dates(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion succeeds with valid dates (check_out > check_in)"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=10),  # After check_in
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        assert result is not None
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking.check_in == request_data.check_in
        assert booking.check_out == request_data.check_out
    
    def test_conversion_invoice_not_found(
        self,
        db: Session,
        admin_user: User
    ):
        """Test conversion fails when invoice doesn't exist"""
        non_existent_id = 999999
        request_data = InvoiceToBookingRequest(
            invoice_id=non_existent_id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=non_existent_id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()


class TestInvoiceToBookingAccessControl:
    """Test role-based access control for invoice-to-booking conversion"""
    
    def test_admin_can_convert_any_invoice(
        self,
        db: Session,
        admin_user: User,
        regular_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test admin can convert invoices created by any user"""
        # Create invoice by regular user
        invoice = create_test_invoice(
            db, regular_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # Admin should be able to convert
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        assert result is not None
        assert result["invoice_id"] == invoice.id
    
    def test_finance_can_convert_any_invoice(
        self,
        db: Session,
        finance_user: User,
        regular_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test finance user can convert invoices created by any user"""
        # Create invoice by regular user
        invoice = create_test_invoice(
            db, regular_user, test_customer, test_package, test_villa,
            status="paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # Finance should be able to convert
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=finance_user
        )
        
        assert result is not None
    
    def test_sales_can_convert_any_invoice(
        self,
        db: Session,
        sales_user: User,
        regular_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test sales user can convert invoices created by any user"""
        # Create invoice by regular user
        invoice = create_test_invoice(
            db, regular_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # Sales should be able to convert
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=sales_user
        )
        
        assert result is not None
    
    def test_regular_user_can_convert_own_invoice(
        self,
        db: Session,
        regular_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test regular user can convert their own invoices"""
        # Create invoice by regular user
        invoice = create_test_invoice(
            db, regular_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        # Regular user should be able to convert their own invoice
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=regular_user
        )
        
        assert result is not None


class TestInvoiceToBookingDataIntegrity:
    """Test data integrity during invoice-to-booking conversion"""
    
    def test_conversion_data_mapping(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test all data is correctly mapped from invoice to booking"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid",
            total=Decimal("52000000.00")
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=6,
            notes="Test booking notes"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        
        # Verify all field mappings
        assert booking.user_id == invoice.user_id
        assert booking.customer_id == invoice.customer_id
        assert booking.sales_person_id == invoice.sales_person_id
        assert booking.check_in == request_data.check_in
        assert booking.check_out == request_data.check_out
        assert booking.total_pax == request_data.total_pax
        assert booking.status == "pending"
        assert booking.notes == request_data.notes
        assert booking.total == invoice.total
        assert booking.tax_total == invoice.tax_total
        assert booking.amount_paid == invoice.amount_paid  # Preserves payment from invoice
        assert booking.amount_due == invoice.amount_due    # Preserves remaining balance from invoice
    
    def test_conversion_items_copied(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test invoice items are copied to booking items"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        booking_items = db.query(BookingItem).filter(BookingItem.booking_id == booking.id).all()
        invoice_items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).all()
        
        # Verify same number of items
        assert len(booking_items) == len(invoice_items)
        
        # Verify item details match
        for invoice_item, booking_item in zip(invoice_items, booking_items):
            assert booking_item.package_id == invoice_item.package_id
            assert booking_item.unit_price == invoice_item.unit_price
            assert booking_item.discount == invoice_item.discount
            assert booking_item.pax == invoice_item.pax
            assert booking_item.line_total == invoice_item.line_total
    
    def test_conversion_villas_copied(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test invoice villas are copied to booking villas"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        booking_villas = db.query(BookingVilla).filter(BookingVilla.booking_id == booking.id).all()
        invoice_villas = db.query(InvoiceVilla).filter(InvoiceVilla.invoice_id == invoice.id).all()
        
        # Verify same number of villas
        assert len(booking_villas) == len(invoice_villas)
        
        # Verify villa IDs match
        invoice_villa_ids = {iv.villa_id for iv in invoice_villas}
        booking_villa_ids = {bv.villa_id for bv in booking_villas}
        assert invoice_villa_ids == booking_villa_ids
    
    def test_conversion_creates_unique_booking_code(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test each conversion creates a unique booking code"""
        # Create two invoices
        invoice1 = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        invoice2 = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="paid"
        )
        
        request1 = InvoiceToBookingRequest(
            invoice_id=invoice1.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        request2 = InvoiceToBookingRequest(
            invoice_id=invoice2.id,
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=13),
            total_pax=3
        )
        
        result1 = convert_invoice_to_booking(db, invoice1.id, request1, admin_user)
        result2 = convert_invoice_to_booking(db, invoice2.id, request2, admin_user)
        
        # Verify unique booking codes
        assert result1["booking_code"] != result2["booking_code"]


class TestInvoiceToBookingHistoryRecording:
    """Test history event recording for invoice-to-booking conversion"""
    
    def test_conversion_invoice_history_recorded(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test invoice history is correctly recorded"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Query invoice history
        history = db.query(InvoiceHistory).filter(
            InvoiceHistory.invoice_id == invoice.id,
            InvoiceHistory.event_type == "invoice_converted_to_booking"
        ).first()
        
        assert history is not None
        assert history.event_category == "lifecycle"
        assert history.user_id == admin_user.id
        assert "converted to booking" in history.description.lower()
        assert history.event_metadata is not None
        assert "booking_id" in history.event_metadata
        assert "booking_code" in history.event_metadata
        assert history.event_metadata["booking_id"] == result["booking_id"]
    
    def test_conversion_booking_history_recorded(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test booking history is correctly recorded"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Query booking history
        history_entries = db.query(BookingHistory).filter(
            BookingHistory.booking_id == result["booking_id"],
            BookingHistory.change_type == "created"
        ).all()
        
        assert len(history_entries) >= 2  # At least conversion_source and source_invoice
        
        # Check for conversion_source entry
        conversion_source = next(
            (h for h in history_entries if h.field_name == "conversion_source"),
            None
        )
        assert conversion_source is not None
        assert conversion_source.new_value == "invoice"
        assert conversion_source.user_id == admin_user.id
        
        # Check for source_invoice entry
        source_invoice = next(
            (h for h in history_entries if h.field_name == "source_invoice"),
            None
        )
        assert source_invoice is not None
        assert invoice.invoice_number in source_invoice.new_value
    
    def test_conversion_history_contains_metadata(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test conversion history metadata contains relevant details"""
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid"
        )
        
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Check invoice history metadata
        invoice_history = db.query(InvoiceHistory).filter(
            InvoiceHistory.invoice_id == invoice.id,
            InvoiceHistory.event_type == "invoice_converted_to_booking"
        ).first()
        
        assert invoice_history.event_metadata is not None
        assert "booking_id" in invoice_history.event_metadata
        assert "booking_code" in invoice_history.event_metadata
        assert "total_amount" in invoice_history.event_metadata
        assert "customer_name" in invoice_history.event_metadata
        assert invoice_history.event_metadata["customer_name"] == test_customer.name