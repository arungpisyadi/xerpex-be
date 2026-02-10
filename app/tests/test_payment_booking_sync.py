"""
Tests for payment and booking sync functionality

This test suite verifies:
1. Invoice booking_id is set when invoice is converted to booking
2. Payment creation uses SUM formula to calculate amount_paid
3. Payment deletion recalculates amount_paid correctly
4. Booking amount_paid is synced when payments are created/deleted
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.payment import Invoice, InvoiceItem, InvoiceVilla, Payment
from app.models.booking import Booking, BookingItem, BookingVilla
from app.schemas.payment import PaymentCreate, PaymentUpdate, PaymentMethod, PaymentType, PaymentStatus, InvoiceStatus
from app.schemas.payment import InvoiceToBookingRequest
from app.services.payment import create_payment, delete_payment, update_payment, convert_invoice_to_booking


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing"""
    user = User(
        username="admin_payment_sync",
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
        name="Test Customer for Payment Sync",
        email="payment_sync_customer@test.com",
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
        name="Test Package for Payment Sync",
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
        name="Test Villa for Payment Sync",
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
    status: str = "draft",
    total: Decimal = Decimal("5000000.00"),
    amount_paid: Decimal = Decimal("0.00")
) -> Invoice:
    """Helper function to create a test invoice with items and villas"""
    invoice = Invoice(
        user_id=user.id,
        customer_id=customer.id,
        invoice_number=f"INV-SYNC-{datetime.utcnow().timestamp()}",
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
        notes="Test invoice for payment sync",
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
        pax=10,
        line_total=Decimal("5000000.00"),
        created_at=datetime.utcnow()
    )
    db.add(item)
    
    # Add invoice villa
    invoice_villa = InvoiceVilla(
        invoice_id=invoice.id,
        villa_id=villa.id
    )
    db.add(invoice_villa)
    
    # Create initial payment record if amount_paid > 0
    if amount_paid > Decimal("0.00"):
        initial_payment = Payment(
            created_by=user.id,
            invoice_id=invoice.id,
            amount=amount_paid,
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number=f"PAY-INITIAL-{datetime.utcnow().timestamp()}",
            status=PaymentStatus.completed,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(initial_payment)
    
    db.commit()
    db.refresh(invoice)
    return invoice


# ============================================================================
# Test: Invoice booking_id is set after conversion
# ============================================================================

class TestInvoiceBookingIdSet:
    """Test that invoice.booking_id is set when converting to booking"""
    
    def test_invoice_booking_id_set_after_conversion(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test that invoice.booking_id is set after conversion to booking"""
        # Create a partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid",
            amount_paid=Decimal("1000000.00")
        )
        
        # Verify booking_id is None before conversion
        assert invoice.booking_id is None
        
        # Convert to booking
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted from partially paid invoice"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Refresh invoice from database
        db.refresh(invoice)
        
        # Verify invoice.booking_id is now set
        assert invoice.booking_id is not None
        assert invoice.booking_id == result["booking_id"]
    
    def test_invoice_booking_id_links_correctly(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test that invoice.booking_id correctly links to the created booking"""
        # Create a paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="paid",
            amount_paid=Decimal("5000000.00")
        )
        
        # Convert to booking
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted from paid invoice"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        # Verify the booking exists and matches
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking is not None
        
        # Verify invoice.booking_id points to this booking
        db.refresh(invoice)
        assert invoice.booking_id == booking.id


# ============================================================================
# Test: Payment creation with SUM formula
# ============================================================================

class TestPaymentCreationWithSum:
    """Test that payment creation uses SUM formula for amount_paid"""
    
    def test_payment_creation_single_payment(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test creating a single payment calculates amount_paid correctly"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-SINGLE-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-SUM-001",
            status=PaymentStatus.completed
        )
        
        payment = create_payment(db, payment_data, admin_user.id)
        
        # Verify payment was created
        assert payment.id is not None
        
        # Refresh invoice and verify amount_paid
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("300.00")
        assert invoice.amount_due == Decimal("700.00")
    
    def test_payment_creation_multiple_payments(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test creating multiple payments accumulates correctly using SUM"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-MULTI-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create first payment
        payment1_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-MULTI-001",
            status=PaymentStatus.completed
        )
        payment1 = create_payment(db, payment1_data, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("300.00")
        
        # Create second payment
        payment2_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("400.00"),
            payment_method=PaymentMethod.cash,
            payment_type=PaymentType.installment,
            payment_date=date.today(),
            reference_number="PAY-MULTI-002",
            status=PaymentStatus.completed
        )
        payment2 = create_payment(db, payment2_data, admin_user.id)
        
        db.refresh(invoice)
        # SUM of all payments: 300 + 400 = 700
        assert invoice.amount_paid == Decimal("700.00")
        assert invoice.amount_due == Decimal("300.00")
        
        # Create third payment
        payment3_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.credit_card,
            payment_type=PaymentType.paid_off,
            payment_date=date.today(),
            reference_number="PAY-MULTI-003",
            status=PaymentStatus.completed
        )
        payment3 = create_payment(db, payment3_data, admin_user.id)
        
        db.refresh(invoice)
        # SUM of all payments: 300 + 400 + 300 = 1000
        assert invoice.amount_paid == Decimal("1000.00")
        assert invoice.amount_due == Decimal("0.00")
        assert invoice.status == InvoiceStatus.paid.value


# ============================================================================
# Test: Payment deletion recalculates amount_paid
# ============================================================================

class TestPaymentDeletionRecalculation:
    """Test that payment deletion recalculates amount_paid correctly"""
    
    def test_delete_single_payment_resets_amount_paid(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test deleting a single payment resets amount_paid to 0"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-DEL-SINGLE-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-DEL-SINGLE-001",
            status=PaymentStatus.completed
        )
        payment = create_payment(db, payment_data, admin_user.id)
        payment_id = payment.id
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("500.00")
        
        # Delete the payment
        result = delete_payment(db, payment_id, admin_user.id)
        assert result is True
        
        # Verify payment was deleted
        deleted_payment = db.query(Payment).filter(Payment.id == payment_id).first()
        assert deleted_payment is None
        
        # Verify amount_paid is recalculated
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("0.00")
        assert invoice.amount_due == Decimal("1000.00")
    
    def test_delete_one_of_multiple_payments_recalculates(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test deleting one payment recalculates correctly from remaining payments"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-DEL-MULTI-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create multiple payments
        payment1_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-DEL-MULTI-001",
            status=PaymentStatus.completed
        )
        payment1 = create_payment(db, payment1_data, admin_user.id)
        
        payment2_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("400.00"),
            payment_method=PaymentMethod.cash,
            payment_type=PaymentType.installment,
            payment_date=date.today(),
            reference_number="PAY-DEL-MULTI-002",
            status=PaymentStatus.completed
        )
        payment2 = create_payment(db, payment2_data, admin_user.id)
        
        payment3_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.credit_card,
            payment_type=PaymentType.paid_off,
            payment_date=date.today(),
            reference_number="PAY-DEL-MULTI-003",
            status=PaymentStatus.completed
        )
        payment3 = create_payment(db, payment3_data, admin_user.id)
        
        db.refresh(invoice)
        # Total: 300 + 400 + 300 = 1000
        assert invoice.amount_paid == Decimal("1000.00")
        
        # Delete the second payment (400)
        result = delete_payment(db, payment2.id, admin_user.id)
        assert result is True
        
        # Verify remaining payments: 300 + 300 = 600
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("600.00")
        assert invoice.amount_due == Decimal("400.00")
        assert invoice.status == InvoiceStatus.partially_paid.value
    
    def test_delete_last_payment_resets_to_zero(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test deleting the last payment resets amount_paid to 0"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-DEL-LAST-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create two payments
        payment1_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-DEL-LAST-001",
            status=PaymentStatus.completed
        )
        payment1 = create_payment(db, payment1_data, admin_user.id)
        
        payment2_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("700.00"),
            payment_method=PaymentMethod.cash,
            payment_type=PaymentType.paid_off,
            payment_date=date.today(),
            reference_number="PAY-DEL-LAST-002",
            status=PaymentStatus.completed
        )
        payment2 = create_payment(db, payment2_data, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("1000.00")
        
        # Delete first payment
        result = delete_payment(db, payment1.id, admin_user.id)
        assert result is True
        
        db.refresh(invoice)
        # Remaining: 700
        assert invoice.amount_paid == Decimal("700.00")
        
        # Delete second (last) payment
        result = delete_payment(db, payment2.id, admin_user.id)
        assert result is True
        
        db.refresh(invoice)
        # No payments remaining
        assert invoice.amount_paid == Decimal("0.00")
        assert invoice.amount_due == Decimal("1000.00")


# ============================================================================
# Test: Booking amount_paid sync on payment creation/deletion
# ============================================================================

class TestBookingAmountPaidSync:
    """Test that booking amount_paid is synced when payments are created/deleted"""
    
    def test_booking_amount_paid_updated_on_payment_creation(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test that booking amount_paid is updated when payment is created"""
        # Create a partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid",
            amount_paid=Decimal("1000000.00")
        )
        
        # Convert to booking
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted for payment sync test"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking.amount_paid == Decimal("1000000.00")
        assert booking.amount_due == Decimal("4000000.00")
        
        # Create a new payment on the invoice (not the initial one that came with it)
        new_payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.installment,
            payment_date=date.today(),
            reference_number="PAY-BOOKING-SYNC-001",
            status=PaymentStatus.completed
        )
        new_payment = create_payment(db, new_payment_data, admin_user.id)
        
        # Refresh booking and verify amount_paid is updated
        db.refresh(booking)
        # SUM of all payments: 1000000 + 500000 = 1500000
        assert booking.amount_paid == Decimal("1500000.00")
        assert booking.amount_due == Decimal("3500000.00")
    
    def test_booking_amount_paid_updated_on_payment_deletion(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test that booking amount_paid is updated when payment is deleted"""
        # Create a partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid",
            amount_paid=Decimal("1000000.00")
        )
        
        # Add an additional payment before conversion
        pre_payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-PRE-001",
            status=PaymentStatus.completed
        )
        pre_payment = create_payment(db, pre_payment_data, admin_user.id)
        
        # Refresh to get current state
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("1500000.00")
        
        # Convert to booking
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted for payment deletion sync test"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        # Total: 1000000 + 500000 = 1500000
        assert booking.amount_paid == Decimal("1500000.00")
        
        # Delete the pre-existing payment
        result = delete_payment(db, pre_payment.id, admin_user.id)
        assert result is True
        
        # Refresh booking and verify amount_paid is updated
        db.refresh(booking)
        # Remaining: 1000000
        assert booking.amount_paid == Decimal("1000000.00")
        assert booking.amount_due == Decimal("4000000.00")
    
    def test_booking_sync_with_no_booking_linked(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that payment creation works when no booking is linked to invoice"""
        # Create an invoice directly (not converted from quote)
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-NO-BOOKING-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00"),
            booking_id=None  # No booking linked
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Verify no booking_id
        assert invoice.booking_id is None
        
        # Create a payment - should work without errors
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-NO-BOOKING-001",
            status=PaymentStatus.completed
        )
        
        payment = create_payment(db, payment_data, admin_user.id)
        
        # Verify payment was created successfully
        assert payment.id is not None
        
        # Verify invoice amount_paid was updated
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("500.00")
        assert invoice.amount_due == Decimal("500.00")


# ============================================================================
# Test: Edge cases
# ============================================================================

class TestPaymentSyncEdgeCases:
    """Test edge cases for payment and booking sync"""
    
    def test_invoice_without_initial_payment_converted_to_booking(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test converting invoice with 0 amount_paid to booking"""
        # Create a draft invoice (no payments)
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="draft",
            amount_paid=Decimal("0.00")
        )
        
        # Convert to booking - should fail because status is draft
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted from draft invoice"
        )
        
        # Should raise HTTPException because status is not partially_paid or paid
        with pytest.raises(HTTPException) as exc_info:
            convert_invoice_to_booking(
                db=db,
                invoice_id=invoice.id,
                request_data=request_data,
                current_user=admin_user
            )
        
        assert exc_info.value.status_code == 400
    
    def test_multiple_payments_sum_correctness(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that SUM formula correctly calculates various payment amounts"""
        # Create an invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-SUM-TEST-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("10000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("10000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create various payments
        payments = [
            Decimal("123.45"),
            Decimal("456.78"),
            Decimal("789.01"),
            Decimal("2345.67"),
            Decimal("5678.90")
        ]
        
        for i, amount in enumerate(payments):
            payment_data = PaymentCreate(
                invoice_id=invoice.id,
                amount=amount,
                payment_method=PaymentMethod.bank_transfer,
                payment_type=PaymentType.installment,
                payment_date=date.today(),
                reference_number=f"PAY-SUM-TEST-{i}",
                status=PaymentStatus.completed
            )
            create_payment(db, payment_data, admin_user.id)
        
        db.refresh(invoice)
        
        # Verify total matches SUM of all payments
        expected_total = sum(payments)
        assert invoice.amount_paid == expected_total
        assert invoice.amount_due == Decimal("10000.00") - expected_total


# ============================================================================
# Test: Payment update recalculates amount_paid
# ============================================================================

class TestPaymentUpdateRecalculation:
    """Test that payment update recalculates amount_paid correctly"""
    
    def test_update_payment_amount_recalculates_invoice_amount_paid(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that updating payment amount recalculates invoice amount_paid"""
        # Create an invoice directly
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-UPDATE-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-UPDATE-001",
            status=PaymentStatus.completed
        )
        payment = create_payment(db, payment_data, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("300.00")
        
        # Update the payment amount
        payment_update = PaymentUpdate(amount=Decimal("500.00"))
        updated_payment = update_payment(db, payment.id, payment_update, admin_user.id)
        
        # Verify payment was updated
        assert updated_payment.amount == Decimal("500.00")
        
        # Verify invoice amount_paid was recalculated
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("500.00")
        assert invoice.amount_due == Decimal("500.00")
    
    def test_update_payment_amount_with_multiple_payments(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that updating one payment amount recalculates correctly with multiple payments"""
        # Create an invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-UPDATE-MULTI-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create multiple payments
        payment1_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("300.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-UPD-MULTI-001",
            status=PaymentStatus.completed
        )
        payment1 = create_payment(db, payment1_data, admin_user.id)
        
        payment2_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("400.00"),
            payment_method=PaymentMethod.cash,
            payment_type=PaymentType.installment,
            payment_date=date.today(),
            reference_number="PAY-UPD-MULTI-002",
            status=PaymentStatus.completed
        )
        payment2 = create_payment(db, payment2_data, admin_user.id)
        
        db.refresh(invoice)
        # Total: 300 + 400 = 700
        assert invoice.amount_paid == Decimal("700.00")
        
        # Update payment1 from 300 to 500
        payment_update = PaymentUpdate(amount=Decimal("500.00"))
        update_payment(db, payment1.id, payment_update, admin_user.id)
        
        # New total: 500 + 400 = 900
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("900.00")
        assert invoice.amount_due == Decimal("100.00")
        assert invoice.status == InvoiceStatus.partially_paid.value
    
    def test_update_payment_amount_to_full_payment(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that updating payment to full amount marks invoice as paid"""
        # Create an invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-UPDATE-FULL-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a partial payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("600.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-UPDATE-FULL-001",
            status=PaymentStatus.completed
        )
        payment = create_payment(db, payment_data, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("600.00")
        assert invoice.status == InvoiceStatus.partially_paid.value
        
        # Update payment to full amount
        payment_update = PaymentUpdate(amount=Decimal("1000.00"))
        update_payment(db, payment.id, payment_update, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("1000.00")
        assert invoice.amount_due == Decimal("0.00")
        assert invoice.status == InvoiceStatus.paid.value
    
    def test_update_payment_amount_updates_booking_amount_paid(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        test_package: Package,
        test_villa: Villa
    ):
        """Test that updating payment amount syncs to linked booking"""
        # Create a partially_paid invoice
        invoice = create_test_invoice(
            db, admin_user, test_customer, test_package, test_villa,
            status="partially_paid",
            amount_paid=Decimal("1000000.00")
        )
        
        # Convert to booking
        request_data = InvoiceToBookingRequest(
            invoice_id=invoice.id,
            check_in=date.today() + timedelta(days=5),
            check_out=date.today() + timedelta(days=8),
            total_pax=4,
            notes="Converted for payment update sync test"
        )
        
        result = convert_invoice_to_booking(
            db=db,
            invoice_id=invoice.id,
            request_data=request_data,
            current_user=admin_user
        )
        
        booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
        assert booking.amount_paid == Decimal("1000000.00")
        
        # Add another payment
        new_payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.installment,
            payment_date=date.today(),
            reference_number="PAY-UPDATE-BOOKING-001",
            status=PaymentStatus.completed
        )
        new_payment = create_payment(db, new_payment_data, admin_user.id)
        
        db.refresh(booking)
        # Total: 1000000 + 500000 = 1500000
        assert booking.amount_paid == Decimal("1500000.00")
        
        # Update the new payment amount
        payment_update = PaymentUpdate(amount=Decimal("1000000.00"))
        update_payment(db, new_payment.id, payment_update, admin_user.id)
        
        # New total: 1000000 + 1000000 = 2000000
        db.refresh(booking)
        assert booking.amount_paid == Decimal("2000000.00")
        assert booking.amount_due == Decimal("3000000.00")
    
    def test_update_payment_non_amount_fields_no_recalculation(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that updating non-amount fields doesn't trigger recalculation"""
        # Create an invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-UPDATE-NOAMT-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("500.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.down_payment,
            payment_date=date.today(),
            reference_number="PAY-UPDATE-NOAMT-001",
            status=PaymentStatus.completed
        )
        payment = create_payment(db, payment_data, admin_user.id)
        
        db.refresh(invoice)
        initial_amount_paid = invoice.amount_paid
        
        # Update payment notes only
        payment_update = PaymentUpdate(notes="Updated payment notes")
        updated_payment = update_payment(db, payment.id, payment_update, admin_user.id)
        
        # Verify payment was updated
        assert updated_payment.notes == "Updated payment notes"
        
        # Verify invoice amount_paid is unchanged
        db.refresh(invoice)
        assert invoice.amount_paid == initial_amount_paid
    
    def test_update_payment_reduces_amount_updates_status(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer
    ):
        """Test that reducing payment amount updates invoice status from paid to partially_paid"""
        # Create an invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number=f"INV-UPDATE-REDUCE-{datetime.utcnow().timestamp()}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000.00"),
            amount_paid=Decimal("0.00"),
            amount_due=Decimal("1000.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create a full payment
        payment_data = PaymentCreate(
            invoice_id=invoice.id,
            amount=Decimal("1000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_type=PaymentType.paid_off,
            payment_date=date.today(),
            reference_number="PAY-UPDATE-REDUCE-001",
            status=PaymentStatus.completed
        )
        payment = create_payment(db, payment_data, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("1000.00")
        assert invoice.status == InvoiceStatus.paid.value
        
        # Reduce payment amount
        payment_update = PaymentUpdate(amount=Decimal("500.00"))
        update_payment(db, payment.id, payment_update, admin_user.id)
        
        db.refresh(invoice)
        assert invoice.amount_paid == Decimal("500.00")
        assert invoice.amount_due == Decimal("500.00")
        assert invoice.status == InvoiceStatus.partially_paid.value
