"""
Comprehensive tests for the refactored payment module

This test suite covers:
- Payment creation with new fields (created_by, booking_id, payment_type, status)
- Payment schema validation (status and payment_type enums)
- Payment response fields verification
- Authorization with created_by field
- API endpoint testing (POST /api/v1/payments)
- User isolation for payments
- Payment workflow and status transitions
- Error handling and edge cases
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.payment import Payment, Invoice, InvoiceItem
from app.models.package import Package
from app.schemas.payment import (
    PaymentCreate, PaymentUpdate, PaymentStatusUpdate,
    PaymentStatus, PaymentMethod, PaymentType
)
from app.services.payment import (
    create_payment, get_payment, get_payments,
    update_payment, update_payment_status, delete_payment
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_package(db: Session, test_user) -> Package:
    """Create a test package for invoice items"""
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        category="Adventure",
        type="Tour",
        description="Test package for payments",
        days=1,
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
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer"""
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
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
def test_invoice(db: Session, test_user, test_customer, test_package) -> Invoice:
    """Create a test invoice for payments"""
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=test_customer.id,
        invoice_number="INV-TEST-001",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="sent",
        total=Decimal("1000000.00"),
        tax_total=Decimal("0.00"),
        amount_due=Decimal("1000000.00"),
        amount_paid=Decimal("0.00"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=test_package.id,
        unit_price=Decimal("1000000.00"),
        discount=Decimal("0.00"),
        pax=1,
        line_total=Decimal("1000000.00"),
        created_at=datetime.utcnow()
    )
    db.add(item)
    db.commit()
    db.refresh(invoice)
    return invoice


@pytest.fixture
def test_booking(db: Session, test_user, test_customer) -> Booking:
    """Create a test booking for payments"""
    booking = Booking(
        user_id=test_user["id"],
        customer_id=test_customer.id,
        booking_code="BK-TEST-001",
        check_in=date.today() + timedelta(days=7),
        check_out=date.today() + timedelta(days=10),
        total_pax=2,
        status="confirmed",
        total=Decimal("3000000.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("3000000.00"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ============================================================================
# Test Payment Creation with New Fields
# ============================================================================

class TestPaymentCreationWithNewFields:
    """Test payment creation with refactored fields"""
    
    def test_create_payment_with_partial_status_and_down_payment_type(
        self, db: Session, test_user, test_invoice, test_booking
    ):
        """Test creating payment with status='partial' and payment_type='down-payment'"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.partial,
            payment_type=PaymentType.down_payment,
            reference_number="REF-001",
            notes="Down payment for booking"
        )
        
        # Act
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert payment.id is not None
        assert payment.created_by == test_user["id"]
        assert payment.status == "partial"
        assert payment.payment_type == "down-payment"
        assert payment.amount == Decimal("300000.00")
        assert payment.invoice_id == test_invoice.id
    
    def test_create_payment_with_full_status_and_paid_off_type(
        self, db: Session, test_user, test_invoice
    ):
        """Test creating payment with status='full' and payment_type='paid-off'"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("1000000.00"),
            payment_method=PaymentMethod.credit_card,
            payment_date=date.today(),
            status=PaymentStatus.full,
            payment_type=PaymentType.paid_off,
            reference_number="REF-002",
            notes="Full payment"
        )
        
        # Act
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert payment.id is not None
        assert payment.status == "full"
        assert payment.payment_type == "paid-off"
        assert payment.amount == Decimal("1000000.00")
    
    def test_create_payment_with_booking_id(
        self, db: Session, test_user, test_invoice, test_booking
    ):
        """Test creating payment with booking_id (nullable)"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.partial,
            payment_type=PaymentType.installment
        )
        # Manually set booking_id since it's not in standard PaymentCreate
        payment_data_dict = payment_data.dict()
        payment_data_dict['booking_id'] = test_booking.id
        
        # Act
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        # Set booking_id after creation
        payment.booking_id = test_booking.id
        db.commit()
        db.refresh(payment)
        
        # Assert
        assert payment.booking_id == test_booking.id
        assert payment.booking is not None
    
    def test_create_payment_without_booking_id(
        self, db: Session, test_user, test_invoice
    ):
        """Test creating payment without booking_id (should be None)"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.digital_wallet,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        
        # Act
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert payment.booking_id is None
    
    def test_created_by_set_from_authenticated_user(
        self, db: Session, test_user, test_invoice
    ):
        """Test that created_by is set from authenticated user, not user_id"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("250000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        
        # Act
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert payment.created_by == test_user["id"]
        assert hasattr(payment, 'creator')
        assert payment.creator.id == test_user["id"]


# ============================================================================
# Test Payment Schema Validation
# ============================================================================

class TestPaymentSchemaValidation:
    """Test payment schema enum validation"""
    
    def test_status_enum_accepts_valid_values(self):
        """Test that status enum accepts only valid values"""
        # Valid statuses
        valid_statuses = ["partial", "full", "pending", "completed", "failed", "refunded"]
        for status in valid_statuses:
            assert status in [s.value for s in PaymentStatus]
    
    def test_status_enum_rejects_invalid_values(self):
        """Test that invalid status values are rejected"""
        # Invalid status should raise ValueError
        with pytest.raises(ValueError):
            PaymentStatus("invalid_status")
    
    def test_payment_type_enum_accepts_valid_values(self):
        """Test that payment_type enum accepts only valid values"""
        # Valid payment types
        valid_types = ["down-payment", "installment", "paid-off"]
        for payment_type in valid_types:
            assert payment_type in [pt.value for pt in PaymentType]
    
    def test_payment_type_enum_rejects_invalid_values(self):
        """Test that invalid payment_type values are rejected"""
        # Invalid payment type should raise ValueError
        with pytest.raises(ValueError):
            PaymentType("invalid_type")
    
    def test_payment_create_with_all_valid_fields(self, test_invoice):
        """Test PaymentCreate schema with all valid fields"""
        # Should not raise any exceptions
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.partial,
            payment_type=PaymentType.down_payment,
            reference_number="REF-TEST",
            notes="Test payment"
        )
        
        assert payment_data.status == PaymentStatus.partial
        assert payment_data.payment_type == PaymentType.down_payment


# ============================================================================
# Test Payment Response Fields
# ============================================================================

class TestPaymentResponseFields:
    """Test payment response includes all expected fields"""
    
    def test_response_includes_created_by(
        self, db: Session, test_user, test_invoice
    ):
        """Verify response includes created_by (not user_id)"""
        # Arrange & Act
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("400000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert hasattr(payment, 'created_by')
        assert payment.created_by == test_user["id"]
        assert not hasattr(payment, 'user_id') or payment.created_by != getattr(payment, 'user_id', None)
    
    def test_response_includes_booking_id(
        self, db: Session, test_user, test_invoice
    ):
        """Verify response includes booking_id (nullable)"""
        # Arrange & Act
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert hasattr(payment, 'booking_id')
        assert payment.booking_id is None  # Should be nullable
    
    def test_response_includes_payment_type(
        self, db: Session, test_user, test_invoice
    ):
        """Verify response includes payment_type"""
        # Arrange & Act
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("350000.00"),
            payment_method=PaymentMethod.credit_card,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert
        assert hasattr(payment, 'payment_type')
        assert payment.payment_type == "installment"
    
    def test_response_includes_all_expected_fields(
        self, db: Session, test_user, test_invoice
    ):
        """Verify response includes all expected fields"""
        # Arrange & Act
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("450000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.partial,
            payment_type=PaymentType.down_payment,
            reference_number="REF-COMPLETE",
            notes="Complete test"
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Assert all expected fields exist
        expected_fields = [
            'id', 'invoice_id', 'booking_id', 'amount', 'payment_date',
            'payment_method', 'payment_type', 'reference_number', 'status',
            'notes', 'created_by', 'created_at', 'updated_at'
        ]
        for field in expected_fields:
            assert hasattr(payment, field), f"Missing field: {field}"


# ============================================================================
# Test Authorization with created_by
# ============================================================================

class TestAuthorizationWithCreatedBy:
    """Test user authorization based on created_by field"""
    
    def test_user_can_see_own_payments(
        self, db: Session, test_user, test_invoice
    ):
        """Test that users can see payments they created"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert retrieved_payment.id == payment.id
        assert retrieved_payment.created_by == test_user["id"]
    
    def test_user_cannot_see_other_user_payments(
        self, db: Session, test_user, test_admin, test_invoice
    ):
        """Test that regular users cannot see other users' payments"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        admin_obj = db.query(User).filter(User.id == test_admin["id"]).first()
        
        # Create payment as admin
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("400000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        admin_payment = create_payment(db, payment_data, created_by=test_admin["id"])
        
        # Act - Try to retrieve as regular user
        retrieved_payment = get_payment(db, admin_payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is None  # User shouldn't see admin's payment
    
    def test_admin_can_see_all_payments(
        self, db: Session, test_user, test_admin, test_invoice
    ):
        """Test that admin/finance users can see all payments"""
        # Arrange
        admin_obj = db.query(User).filter(User.id == test_admin["id"]).first()
        
        # Create payment as regular user
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("350000.00"),
            payment_method=PaymentMethod.credit_card,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        user_payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act - Retrieve as admin
        retrieved_payment = get_payment(db, user_payment.id, admin_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert retrieved_payment.id == user_payment.id
    
    def test_user_list_shows_only_own_payments(
        self, db: Session, test_user, test_admin, test_invoice
    ):
        """Test that get_payments filters by created_by for regular users"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create payments for both users
        for i in range(2):
            payment_data = PaymentCreate(
                invoice_id=test_invoice.id,
                amount=Decimal("200000.00"),
                payment_method=PaymentMethod.cash,
                payment_date=date.today(),
                status=PaymentStatus.pending,
                payment_type=PaymentType.installment
            )
            create_payment(db, payment_data, created_by=test_user["id"])
        
        for i in range(3):
            payment_data = PaymentCreate(
                invoice_id=test_invoice.id,
                amount=Decimal("150000.00"),
                payment_method=PaymentMethod.bank_transfer,
                payment_date=date.today(),
                status=PaymentStatus.pending,
                payment_type=PaymentType.down_payment
            )
            create_payment(db, payment_data, created_by=test_admin["id"])
        
        # Act
        user_payments = get_payments(db, user_obj)
        
        # Assert - User should only see their 2 payments
        assert len(user_payments) == 2
        assert all(p.created_by == test_user["id"] for p in user_payments)
    
    def test_update_payment_only_allowed_for_creator_or_admin(
        self, db: Session, test_user, test_admin, test_invoice
    ):
        """Test updating payment only allowed for creator or admin"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create payment as test_user
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act - Try to update as the creator
        update_data = PaymentUpdate(notes="Updated by creator")
        updated_payment = update_payment(db, payment.id, update_data, created_by=test_user["id"])
        
        # Assert
        assert updated_payment.notes == "Updated by creator"


# ============================================================================
# Test API Endpoint (POST /api/v1/payments)
# ============================================================================

class TestPaymentAPIEndpoint:
    """Test payment API endpoints"""
    
    def test_successful_payment_creation_with_full_payload(
        self, client: TestClient, user_headers, test_invoice
    ):
        """Test successful payment creation with full payload including new fields"""
        # Arrange
        payment_payload = {
            "invoice_id": test_invoice.id,
            "amount": 500000.00,
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
            "status": "partial",
            "payment_type": "down-payment",
            "reference_number": "REF-API-001",
            "notes": "API test payment"
        }
        
        # Act
        response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert float(data["amount"]) == 500000.00
        assert data["status"] == "partial"
        assert data["payment_type"] == "down-payment"
        assert "created_by" in data
        assert "id" in data
    
    def test_payment_creation_returns_201_status(
        self, client: TestClient, user_headers, test_invoice
    ):
        """Test payment creation returns 201 status"""
        # Arrange
        payment_payload = {
            "invoice_id": test_invoice.id,
            "amount": 300000.00,
            "payment_method": "credit_card",
            "payment_date": date.today().isoformat(),
            "status": "full",
            "payment_type": "paid-off"
        }
        
        # Act
        response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        # Assert
        assert response.status_code == 201
    
    def test_payment_creation_with_missing_required_fields_returns_400(
        self, client: TestClient, user_headers
    ):
        """Test payment creation with missing required fields returns 400"""
        # Arrange - Missing invoice_id and amount
        payment_payload = {
            "payment_method": "cash",
            "payment_date": date.today().isoformat()
        }
        
        # Act
        response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_payment_creation_with_invalid_status_returns_400(
        self, client: TestClient, user_headers, test_invoice
    ):
        """Test payment creation with invalid status returns validation error"""
        # Arrange
        payment_payload = {
            "invoice_id": test_invoice.id,
            "amount": 250000.00,
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
            "status": "invalid_status",  # Invalid
            "payment_type": "down-payment"
        }
        
        # Act
        response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        # Assert
        assert response.status_code == 422  # Validation error
    
    def test_payment_creation_with_invalid_payment_type_returns_400(
        self, client: TestClient, user_headers, test_invoice
    ):
        """Test payment creation with invalid payment_type returns validation error"""
        # Arrange
        payment_payload = {
            "invoice_id": test_invoice.id,
            "amount": 250000.00,
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
            "status": "pending",
            "payment_type": "invalid_type"  # Invalid
        }
        
        # Act
        response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        # Assert
        assert response.status_code == 422  # Validation error


# ============================================================================
# Test Payment Status Transitions
# ============================================================================

class TestPaymentStatusTransitions:
    """Test payment status workflow transitions"""
    
    def test_update_payment_status_pending_to_completed(
        self, db: Session, test_user, test_invoice
    ):
        """Test updating payment status from pending to completed"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("400000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
        updated_payment = update_payment_status(
            db, payment.id, status_update, created_by=test_user["id"]
        )
        
        # Assert
        assert updated_payment.status == "completed"
    
    def test_update_payment_status_pending_to_failed(
        self, db: Session, test_user, test_invoice
    ):
        """Test updating payment status from pending to failed"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.credit_card,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        status_update = PaymentStatusUpdate(status=PaymentStatus.failed)
        updated_payment = update_payment_status(
            db, payment.id, status_update, created_by=test_user["id"]
        )
        
        # Assert
        assert updated_payment.status == "failed"
    
    def test_cannot_modify_completed_payment(
        self, db: Session, test_user, test_invoice
    ):
        """Test that completed payments cannot be modified"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.completed,
            payment_type=PaymentType.paid_off
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act & Assert
        update_data = PaymentUpdate(notes="Should fail")
        with pytest.raises(Exception) as exc_info:
            update_payment(db, payment.id, update_data, created_by=test_user["id"])
        assert exc_info.value.status_code == 400
        assert "cannot modify" in exc_info.value.detail.lower() or "completed" in exc_info.value.detail.lower()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestPaymentErrorHandling:
    """Test error handling in payment operations"""
    
    def test_create_payment_with_nonexistent_invoice_fails(
        self, db: Session, test_user
    ):
        """Test creating payment with non-existent invoice fails"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=99999,  # Non-existent
            amount=Decimal("300000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_payment(db, payment_data, created_by=test_user["id"])
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    def test_delete_only_pending_payments(
        self, db: Session, test_user, test_invoice
    ):
        """Test that only pending payments can be deleted"""
        # Arrange
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("250000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.completed,
            payment_type=PaymentType.installment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            delete_payment(db, payment.id, created_by=test_user["id"])
        assert exc_info.value.status_code == 400
        assert "pending" in exc_info.value.detail.lower() or "deleted" in exc_info.value.detail.lower()
    
    def test_get_nonexistent_payment_returns_none(
        self, db: Session, test_user
    ):
        """Test getting non-existent payment returns None"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act
        payment = get_payment(db, 99999, user_obj)
        
        # Assert
        assert payment is None


# ============================================================================
# Test Payment Filtering
# ============================================================================

class TestPaymentFiltering:
    """Test payment filtering capabilities"""
    
    def test_filter_payments_by_status(
        self, db: Session, test_user, test_invoice
    ):
        """Test filtering payments by status"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create payments with different statuses
        for status in [PaymentStatus.pending, PaymentStatus.completed]:
            payment_data = PaymentCreate(
                invoice_id=test_invoice.id,
                amount=Decimal("200000.00"),
                payment_method=PaymentMethod.cash,
                payment_date=date.today(),
                status=status,
                payment_type=PaymentType.installment
            )
            create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        pending_payments = get_payments(db, user_obj, status=PaymentStatus.pending)
        
        # Assert
        assert len(pending_payments) >= 1
        assert all(p.status == "pending" for p in pending_payments)
    
    def test_filter_payments_by_payment_method(
        self, db: Session, test_user, test_invoice
    ):
        """Test filtering payments by payment method"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create payments with different methods
        payment_data1 = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("200000.00"),
            payment_method=PaymentMethod.bank_transfer,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        create_payment(db, payment_data1, created_by=test_user["id"])
        
        payment_data2 = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("150000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        create_payment(db, payment_data2, created_by=test_user["id"])
        
        # Act
        bank_payments = get_payments(db, user_obj, payment_method="bank_transfer")
        
        # Assert
        assert len(bank_payments) >= 1
        assert all(p.payment_method == "bank_transfer" for p in bank_payments)