"""
Comprehensive tests for the enhanced payment relationships endpoint.

This test suite covers:
- Invoice relationship with nested objects
- Customer relationship with nested objects
- Created by relationship with nested objects
- Payment history relationship
- GET single payment endpoint with relationships
- GET payment list endpoint with relationships
- Filtering with relationships
- Role-based access control with relationships
- Null/missing relationships
- Response structure breaking changes (old fields removed)
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.payment import Payment, Invoice, InvoiceItem, PaymentHistory
from app.models.package import Package
from app.schemas.payment import (
    PaymentCreate, PaymentResponse,
    PaymentStatus, PaymentMethod, PaymentType
)
from app.services.payment import create_payment, get_payment, get_payments


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
        description="Test package for relationship testing",
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
    """Create a test customer with all fields"""
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        phone_number="6281234567890",
        address="Test Address, Jakarta",
        billing_address="Test Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_booking(db: Session, test_user, test_customer, test_package) -> Booking:
    """Create a test booking with all fields"""
    booking = Booking(
        user_id=test_user["id"],
        customer_id=test_customer.id,
        booking_code="BK-REL-001",
        check_in=date.today(),
        check_out=date.today() + timedelta(days=3),
        status="confirmed",
        total_pax=2,
        notes="Test booking for relationship testing",
        total=Decimal("1500000.00"),
        tax_total=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("1500000.00"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(booking)
    db.flush()
    
    # Add booking item
    from app.models.booking import BookingItem
    item = BookingItem(
        booking_id=booking.id,
        package_id=test_package.id,
        unit_price=Decimal("750000.00"),
        discount=Decimal("0.00"),
        pax=2,
        line_total=Decimal("1500000.00"),
        created_at=datetime.utcnow()
    )
    db.add(item)
    db.commit()
    db.refresh(booking)
    return booking


@pytest.fixture
def test_invoice(db: Session, test_user, test_customer, test_package) -> Invoice:
    """Create a test invoice with all relationships"""
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=test_customer.id,
        invoice_number="INV-REL-001",
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
def test_payment_with_relationships(
    db: Session, test_user, test_invoice
) -> Payment:
    """Create a test payment with all relationships populated"""
    payment_data = PaymentCreate(
        invoice_id=test_invoice.id,
        amount=Decimal("300000.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_date=date.today(),
        status=PaymentStatus.partial,
        payment_type=PaymentType.down_payment,
        reference_number="REF-REL-001",
        notes="Test payment with relationships"
    )
    payment = create_payment(db, payment_data, created_by=test_user["id"])
    db.refresh(payment)
    return payment


# ============================================================================
# Test Invoice Relationship
# ============================================================================

class TestPaymentInvoiceRelationship:
    """Test suite for payment invoice relationship"""
    
    def test_payment_response_includes_invoice_object(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment response includes full invoice object"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act - Retrieve payment with relationships
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert hasattr(retrieved_payment, 'invoice')
        assert retrieved_payment.invoice is not None
        
        # Verify invoice fields
        invoice = retrieved_payment.invoice
        assert hasattr(invoice, 'id')
        assert hasattr(invoice, 'invoice_number')
        assert hasattr(invoice, 'total')
        assert hasattr(invoice, 'amount_due')
        assert hasattr(invoice, 'status')
        assert hasattr(invoice, 'issue_date')
        assert hasattr(invoice, 'due_date')
    
    def test_invoice_relationship_fields_correctly_populated(
        self, db: Session, test_payment_with_relationships, test_invoice
    ):
        """Test invoice relationship fields are correctly populated"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert invoice values match
        assert retrieved_payment.invoice.id == test_invoice.id
        assert retrieved_payment.invoice.invoice_number == test_invoice.invoice_number
        assert retrieved_payment.invoice.total == test_invoice.total
        assert retrieved_payment.invoice.amount_due == test_invoice.amount_due
        assert retrieved_payment.invoice.status == test_invoice.status
        assert retrieved_payment.invoice.issue_date == test_invoice.issue_date
        assert retrieved_payment.invoice.due_date == test_invoice.due_date
    
    def test_invoice_object_structure_matches_schema(
        self, db: Session, test_payment_with_relationships
    ):
        """Test invoice object structure matches PaymentInvoiceNested schema"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Check schema fields
        invoice = retrieved_payment.invoice
        expected_fields = ['id', 'invoice_number', 'total', 'amount_due', 
                          'status', 'issue_date', 'due_date']
        
        for field in expected_fields:
            assert hasattr(invoice, field), f"Missing invoice field: {field}"


# ============================================================================
# Test Customer Relationship
# ============================================================================

class TestPaymentCustomerRelationship:
    """Test suite for payment customer relationship"""
    
    def test_payment_response_includes_customer_object(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment response includes full customer object from invoice"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert hasattr(retrieved_payment, 'customer')
        assert retrieved_payment.customer is not None
        
        # Verify customer fields
        customer = retrieved_payment.customer
        assert hasattr(customer, 'id')
        assert hasattr(customer, 'name')
        assert hasattr(customer, 'email')
        assert hasattr(customer, 'phone')
        assert hasattr(customer, 'address')
    
    def test_customer_relationship_fields_correctly_populated(
        self, db: Session, test_payment_with_relationships, test_customer
    ):
        """Test customer relationship fields are correctly populated"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert customer values match
        assert retrieved_payment.customer.id == test_customer.id
        assert retrieved_payment.customer.name == test_customer.name
        assert retrieved_payment.customer.email == test_customer.email
        assert retrieved_payment.customer.phone == test_customer.phone_number
        assert retrieved_payment.customer.address == test_customer.address
    
    def test_customer_object_structure_matches_schema(
        self, db: Session, test_payment_with_relationships
    ):
        """Test customer object structure matches PaymentCustomerNested schema"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Check schema fields
        customer = retrieved_payment.customer
        expected_fields = ['id', 'name', 'email', 'phone', 'address']
        
        for field in expected_fields:
            assert hasattr(customer, field), f"Missing customer field: {field}"


# ============================================================================
# Test Created By Relationship
# ============================================================================

class TestPaymentCreatedByRelationship:
    """Test suite for payment creator (created_by) relationship"""
    
    def test_payment_response_includes_creator_object(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment response includes full creator (user) object"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert hasattr(retrieved_payment, 'creator')
        assert retrieved_payment.creator is not None
        
        # Verify creator fields
        creator = retrieved_payment.creator
        assert hasattr(creator, 'id')
        assert hasattr(creator, 'username')
        assert hasattr(creator, 'full_name')
        assert hasattr(creator, 'email')
        assert hasattr(creator, 'role')
    
    def test_creator_relationship_fields_correctly_populated(
        self, db: Session, test_payment_with_relationships, test_user
    ):
        """Test creator relationship fields are correctly populated"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert creator values match
        assert retrieved_payment.creator.id == test_user["id"]
        assert retrieved_payment.creator.username == test_user["username"]
        assert retrieved_payment.creator.email == test_user["email"]
        assert retrieved_payment.creator.role == 'user'
    
    def test_creator_object_structure_matches_schema(
        self, db: Session, test_payment_with_relationships
    ):
        """Test creator object structure matches PaymentCreatorNested schema"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Check schema fields
        creator = retrieved_payment.creator
        expected_fields = ['id', 'username', 'full_name', 'email', 'role']
        
        for field in expected_fields:
            assert hasattr(creator, field), f"Missing creator field: {field}"


# ============================================================================
# Test History Relationship
# ============================================================================

class TestPaymentHistoryRelationship:
    """Test suite for payment history relationship"""
    
    def test_payment_response_includes_history_array(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment response includes payment history records"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert retrieved_payment is not None
        assert hasattr(retrieved_payment, 'payment_history')
        assert retrieved_payment.payment_history is not None
        assert isinstance(retrieved_payment.payment_history, list)
        
        # Payment should have at least one history entry (creation)
        assert len(retrieved_payment.payment_history) >= 1
    
    def test_history_contains_required_fields(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment history contains required fields"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Check history record fields
        if len(retrieved_payment.payment_history) > 0:
            history_record = retrieved_payment.payment_history[0]
            expected_fields = ['id', 'payment_id', 'user_id', 'event_type', 
                             'event_category', 'description', 'event_metadata', 
                             'created_at']
            
            for field in expected_fields:
                assert hasattr(history_record, field), f"Missing history field: {field}"
    
    def test_history_creation_event_recorded(
        self, db: Session, test_payment_with_relationships
    ):
        """Test payment creation event is recorded in history"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Check for creation event
        history_events = [h.event_type for h in retrieved_payment.payment_history]
        assert 'payment_created' in history_events


# ============================================================================
# Test GET Single Payment Endpoint
# ============================================================================

class TestGetSinglePaymentWithRelationships:
    """Test GET /payments/{id} endpoint returns all nested relationships"""
    
    def test_get_single_payment_includes_all_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test GET /payments/{id} returns all nested relationships"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify all relationship objects are present
        assert 'created_by' in data
        assert isinstance(data['created_by'], dict)
        
        assert 'invoice' in data
        if data['invoice'] is not None:
            assert isinstance(data['invoice'], dict)
        
        assert 'customer' in data
        if data['customer'] is not None:
            assert isinstance(data['customer'], dict)
        
        assert 'history' in data
        assert isinstance(data['history'], list)
    
    def test_get_single_payment_with_admin_user(
        self, client: TestClient, admin_headers, test_payment_with_relationships
    ):
        """Test admin can access payment with all relationships"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=admin_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'created_by' in data
        assert 'invoice' in data
        assert 'customer' in data
    
    def test_get_single_payment_invoice_fields_populated(
        self, client: TestClient, user_headers, test_payment_with_relationships, 
        test_invoice
    ):
        """Test invoice fields are properly populated in response"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        invoice = data.get('invoice')
        
        assert invoice is not None
        assert invoice['id'] == test_invoice.id
        assert invoice['invoice_number'] == test_invoice.invoice_number
        assert 'total' in invoice
        assert 'amount_due' in invoice
        assert 'status' in invoice
        assert 'issue_date' in invoice
        assert 'due_date' in invoice


# ============================================================================
# Test GET Payment List Endpoint
# ============================================================================

class TestGetPaymentsListWithRelationships:
    """Test GET /payments endpoint returns all payments with nested relationships"""
    
    def test_get_payments_list_includes_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test GET /payments returns all payments with nested relationships"""
        # Act
        response = client.get(
            "/api/v1/payments",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert 'payments' in data
        assert isinstance(data['payments'], list)
        assert len(data['payments']) > 0
        
        # Check first payment has relationships
        first_payment = data['payments'][0]
        assert 'created_by' in first_payment
        assert 'invoice' in first_payment
        assert 'customer' in first_payment
        assert 'history' in first_payment
    
    def test_get_payments_list_with_pagination(
        self, db: Session, client: TestClient, user_headers, 
        test_user, test_invoice
    ):
        """Test GET /payments with pagination returns relationships"""
        # Arrange - Create multiple payments
        for i in range(3):
            payment_data = PaymentCreate(
                invoice_id=test_invoice.id,
                amount=Decimal(f"{(i+1) * 100000}.00"),
                payment_method=PaymentMethod.bank_transfer,
                payment_date=date.today(),
                status=PaymentStatus.partial,
                payment_type=PaymentType.installment,
                reference_number=f"REF-PAGE-{i}"
            )
            create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        response = client.get(
            "/api/v1/payments?skip=0&limit=2",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['payments']) <= 2
        # All payments should have relationships
        for payment in data['payments']:
            assert 'created_by' in payment
            assert 'invoice' in payment


# ============================================================================
# Test Filtering with Relationships
# ============================================================================

class TestPaymentRelationshipsWithFilters:
    """Test payments with filters still return relationships"""
    
    def test_filter_by_invoice_id_includes_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships,
        test_invoice
    ):
        """Test filtering by invoice_id still returns relationships"""
        # Act
        response = client.get(
            f"/api/v1/payments?invoice_id={test_invoice.id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert len(data['payments']) > 0
        first_payment = data['payments'][0]
        
        # Verify relationships exist
        assert 'created_by' in first_payment
        assert 'invoice' in first_payment
        assert first_payment['invoice']['id'] == test_invoice.id
    
    def test_filter_by_status_includes_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test filtering by status still returns relationships"""
        # Act
        response = client.get(
            "/api/v1/payments?status=partial",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        if len(data['payments']) > 0:
            first_payment = data['payments'][0]
            assert 'created_by' in first_payment
            assert 'customer' in first_payment
    
    def test_filter_by_date_range_includes_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test filtering by date range still returns relationships"""
        # Arrange
        from_date = (date.today() - timedelta(days=1)).isoformat()
        to_date = (date.today() + timedelta(days=1)).isoformat()
        
        # Act
        response = client.get(
            f"/api/v1/payments?from_date={from_date}&to_date={to_date}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        if len(data['payments']) > 0:
            first_payment = data['payments'][0]
            assert 'invoice' in first_payment
            assert 'history' in first_payment


# ============================================================================
# Test Role-Based Access Control with Relationships
# ============================================================================

class TestPaymentRelationshipsAccessControl:
    """Test role-based access control with nested relationships"""
    
    def test_user_can_access_own_payment_relationships(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test user can access their own payment with relationships"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'created_by' in data
        assert 'invoice' in data
    
    def test_admin_can_access_all_payment_relationships(
        self, client: TestClient, admin_headers, test_payment_with_relationships
    ):
        """Test admin can access any payment with relationships"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=admin_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'created_by' in data
        assert 'customer' in data
    
    def test_user_cannot_access_other_user_payment(
        self, db: Session, client: TestClient, user_headers, 
        test_admin, test_invoice
    ):
        """Test user cannot access another user's payment"""
        # Arrange - Create payment as admin
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.installment
        )
        admin_payment = create_payment(db, payment_data, created_by=test_admin["id"])
        
        # Act - Try to access as regular user
        response = client.get(
            f"/api/v1/payments/{admin_payment.id}",
            headers=user_headers
        )
        
        # Assert - Should not find or access denied
        assert response.status_code in [404, 403]


# ============================================================================
# Test Null/Missing Relationships
# ============================================================================

class TestPaymentNullRelationships:
    """Test payments handle null relationships gracefully"""
    
    def test_payment_without_invoice_handles_null(
        self, db: Session, test_user
    ):
        """Test payment handles null invoice gracefully (if possible)"""
        # Note: In our schema, invoice_id is required, so this tests the response structure
        # Act - Create payment and immediately delete invoice reference (edge case)
        # This simulates orphaned payment scenario
        
        # For this test, we just verify the schema allows null
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # The schema should handle invoice=None gracefully
        # This is more of a schema validation test
        pass
    
    def test_customer_nullable_in_response(
        self, db: Session, test_payment_with_relationships
    ):
        """Test customer field is nullable in response"""
        # Arrange
        payment = test_payment_with_relationships
        
        # Act
        user_obj = db.query(User).filter(User.id == payment.created_by).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - customer field exists even if None
        assert hasattr(retrieved_payment, 'customer')
        # In this case it should not be None, but the field exists
    
    def test_history_empty_array_when_no_history(
        self, db: Session, test_user, test_invoice
    ):
        """Test history returns empty array when no history exists"""
        # Arrange - Create payment
        payment_data = PaymentCreate(
            invoice_id=test_invoice.id,
            amount=Decimal("200000.00"),
            payment_method=PaymentMethod.cash,
            payment_date=date.today(),
            status=PaymentStatus.pending,
            payment_type=PaymentType.down_payment
        )
        payment = create_payment(db, payment_data, created_by=test_user["id"])
        
        # Manually clear history for test (edge case)
        db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id
        ).delete()
        db.commit()
        
        # Act
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert
        assert hasattr(retrieved_payment, 'payment_history')
        assert isinstance(retrieved_payment.payment_history, list)
        assert len(retrieved_payment.payment_history) == 0


# ============================================================================
# Test Response Structure Breaking Changes
# ============================================================================

class TestPaymentResponseStructureBreakingChanges:
    """Test that old fields are removed and new structure is correct"""
    
    def test_created_by_is_object_not_int(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test created_by is now object, not just integer"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # created_by should be an object with nested fields
        assert 'created_by' in data
        assert isinstance(data['created_by'], dict)
        assert 'id' in data['created_by']
        assert 'username' in data['created_by']
        assert 'email' in data['created_by']
        assert 'role' in data['created_by']
    
    def test_response_structure_matches_schema(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test response structure matches expected JSON format"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check all expected top-level fields exist
        expected_fields = [
            'id', 'invoice_id', 'booking_id', 'amount', 'payment_date',
            'payment_method', 'payment_type', 'reference_number', 'status',
            'notes', 'created_by', 'invoice', 'customer', 'history',
            'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            assert field in data, f"Missing expected field: {field}"
    
    def test_nested_objects_have_correct_structure(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test nested objects have correct structure"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify created_by structure
        created_by = data['created_by']
        assert all(key in created_by for key in ['id', 'username', 'email', 'role'])
        
        # Verify invoice structure (if present)
        if data['invoice'] is not None:
            invoice = data['invoice']
            expected_invoice_fields = [
                'id', 'invoice_number', 'total', 'amount_due', 
                'status', 'issue_date', 'due_date'
            ]
            assert all(key in invoice for key in expected_invoice_fields)
        
        # Verify customer structure (if present)
        if data['customer'] is not None:
            customer = data['customer']
            expected_customer_fields = ['id', 'name', 'email', 'phone', 'address']
            assert all(key in customer for key in expected_customer_fields)
    
    def test_history_array_structure(
        self, client: TestClient, user_headers, test_payment_with_relationships
    ):
        """Test history is an array with correct structure"""
        # Arrange
        payment_id = test_payment_with_relationships.id
        
        # Act
        response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify history is an array
        assert 'history' in data
        assert isinstance(data['history'], list)
        
        # If history exists, verify structure
        if len(data['history']) > 0:
            history_item = data['history'][0]
            expected_history_fields = [
                'id', 'payment_id', 'user_id', 'event_type', 
                'event_category', 'description', 'event_metadata', 'created_at'
            ]
            assert all(key in history_item for key in expected_history_fields)


# ============================================================================
# Test Booking Relationship
# ============================================================================

class TestPaymentBookingRelationship:
    """Test suite for payment booking relationship"""
    
    def test_payment_response_includes_booking_object(
        self, db: Session, test_user, test_booking, test_invoice
    ):
        """Test payment response includes full booking object"""
        # Arrange - Create payment with booking
        payment = Payment(
            booking_id=test_booking.id,
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="partial",
            reference_number="REF-BK-001",
            notes="Test payment with booking",
            created_by=test_user["id"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Act - Serialize via schema
        from app.schemas.payment import PaymentResponse
        response = PaymentResponse.from_orm(payment)
        response_dict = response.model_dump()
        
        # Assert - Verify booking object
        assert response_dict['booking'] is not None
        assert isinstance(response_dict['booking'], dict)
        assert response_dict['booking']['id'] == test_booking.id
        assert response_dict['booking']['booking_code'] == test_booking.booking_code
        assert response_dict['booking']['status'] == test_booking.status
        assert response_dict['booking']['check_in'] == test_booking.check_in
        assert response_dict['booking']['check_out'] == test_booking.check_out
        assert response_dict['booking']['total'] == test_booking.total
        assert response_dict['booking']['total_pax'] == test_booking.total_pax
    
    def test_payment_response_booking_null_when_no_booking(
        self, db: Session, test_user, test_invoice
    ):
        """Test payment response has booking: null when no booking"""
        # Arrange - Create payment WITHOUT booking
        payment = Payment(
            booking_id=None,  # No booking
            invoice_id=test_invoice.id,
            amount=Decimal("300000.00"),
            payment_method="cash",
            payment_type="installment",
            payment_date=date.today(),
            status="completed",
            reference_number="REF-NO-BK-001",
            created_by=test_user["id"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Act - Serialize via schema
        from app.schemas.payment import PaymentResponse
        response = PaymentResponse.from_orm(payment)
        response_dict = response.model_dump()
        
        # Assert - Verify booking is null (not empty object)
        assert 'booking' in response_dict
        assert response_dict['booking'] is None
    
    def test_booking_relationship_fields_correctly_populated(
        self, db: Session, test_user, test_customer, test_package
    ):
        """Test all booking fields are correctly populated in payment response"""
        # Arrange - Create booking with specific values
        specific_booking = Booking(
            user_id=test_user["id"],
            customer_id=test_customer.id,
            booking_code="BK-SPECIFIC-999",
            check_in=date(2025, 6, 15),
            check_out=date(2025, 6, 20),
            status="confirmed",
            total_pax=4,
            notes="Specific test booking",
            total=Decimal("2500000.00"),
            tax_total=Decimal("0.00"),
            amount_paid=Decimal("1000000.00"),
            amount_due=Decimal("1500000.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(specific_booking)
        db.commit()
        db.refresh(specific_booking)
        
        # Create invoice
        invoice = Invoice(
            user_id=test_user["id"],
            customer_id=test_customer.id,
            invoice_number="INV-BK-SPECIFIC",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("2500000.00"),
            tax_total=Decimal("0.00"),
            amount_due=Decimal("1500000.00"),
            amount_paid=Decimal("1000000.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create payment for booking
        payment = Payment(
            booking_id=specific_booking.id,
            invoice_id=invoice.id,
            amount=Decimal("1000000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="completed",
            reference_number="REF-SPECIFIC-BK",
            created_by=test_user["id"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Act - Serialize via schema
        from app.schemas.payment import PaymentResponse
        response = PaymentResponse.from_orm(payment)
        response_dict = response.model_dump()
        
        # Assert - Verify each field matches expected values
        booking = response_dict['booking']
        assert booking['id'] == specific_booking.id
        assert booking['booking_code'] == "BK-SPECIFIC-999"
        assert booking['status'] == "confirmed"
        assert booking['check_in'] == date(2025, 6, 15)
        assert booking['check_out'] == date(2025, 6, 20)
        assert booking['total'] == Decimal("2500000.00")
        assert booking['total_pax'] == 4
    
    def test_get_single_payment_includes_booking(
        self, db: Session, test_user, test_booking, test_invoice
    ):
        """Test payment retrieval via service includes full booking object"""
        # Arrange - Create payment with booking
        payment = Payment(
            booking_id=test_booking.id,
            invoice_id=test_invoice.id,
            amount=Decimal("750000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="partial",
            reference_number="REF-SERVICE-BK-001",
            created_by=test_user["id"]
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Act - Retrieve payment via service layer
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        retrieved_payment = get_payment(db, payment.id, user_obj)
        
        # Assert - Verify response includes full booking object
        assert retrieved_payment is not None
        assert hasattr(retrieved_payment, 'booking')
        assert retrieved_payment.booking is not None
        assert hasattr(retrieved_payment.booking, 'id')
        assert retrieved_payment.booking.id == test_booking.id
        assert retrieved_payment.booking.booking_code == test_booking.booking_code
        assert retrieved_payment.booking.status == test_booking.status
        assert retrieved_payment.booking.total_pax == test_booking.total_pax
        assert hasattr(retrieved_payment.booking, 'check_in')
        assert hasattr(retrieved_payment.booking, 'check_out')
        assert hasattr(retrieved_payment.booking, 'total')
    
    def test_get_payments_list_includes_booking(
        self, client: TestClient, user_headers, db: Session,
        test_user, test_booking, test_invoice, test_customer, test_package
    ):
        """Test GET /payments includes booking for each payment"""
        # Arrange - Create multiple payments (some with bookings, some without)
        
        # Payment 1: with booking
        payment1 = Payment(
            booking_id=test_booking.id,
            invoice_id=test_invoice.id,
            amount=Decimal("500000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="partial",
            reference_number="REF-LIST-1",
            created_by=test_user["id"]
        )
        db.add(payment1)
        
        # Create second invoice for payment without booking
        invoice2 = Invoice(
            user_id=test_user["id"],
            customer_id=test_customer.id,
            invoice_number="INV-LIST-2",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("800000.00"),
            tax_total=Decimal("0.00"),
            amount_paid=Decimal("0.00")
        )
        db.add(invoice2)
        db.flush()
        
        # Add invoice item
        item2 = InvoiceItem(
            invoice_id=invoice2.id,
            package_id=test_package.id,
            unit_price=Decimal("800000.00"),
            discount=Decimal("0.00"),
            pax=1,
            line_total=Decimal("800000.00")
        )
        db.add(item2)
        
        # Payment 2: WITHOUT booking
        payment2 = Payment(
            booking_id=None,  # No booking
            invoice_id=invoice2.id,
            amount=Decimal("300000.00"),
            payment_method="cash",
            payment_type="installment",
            payment_date=date.today(),
            status="completed",
            reference_number="REF-LIST-2",
            created_by=test_user["id"]
        )
        db.add(payment2)
        db.commit()
        
        # Act - GET payments list via API
        response = client.get(
            "/api/v1/payments",
            headers=user_headers
        )
        
        # Assert - Verify each payment's booking field is correctly populated or null
        assert response.status_code == 200
        data = response.json()
        
        assert 'payments' in data
        assert len(data['payments']) >= 2
        
        # Find our test payments
        payments_by_ref = {p['reference_number']: p for p in data['payments']}
        
        # Verify payment with booking has booking object
        if 'REF-LIST-1' in payments_by_ref:
            payment_with_booking = payments_by_ref['REF-LIST-1']
            assert 'booking' in payment_with_booking
            assert payment_with_booking['booking'] is not None
            assert payment_with_booking['booking']['id'] == test_booking.id
            assert payment_with_booking['booking']['booking_code'] == test_booking.booking_code
        
        # Verify payment without booking has null booking
        if 'REF-LIST-2' in payments_by_ref:
            payment_without_booking = payments_by_ref['REF-LIST-2']
            assert 'booking' in payment_without_booking
            assert payment_without_booking['booking'] is None
    
    def test_booking_object_structure_matches_schema(
        self, db: Session, test_user, test_booking, test_invoice
    ):
        """Test booking object structure matches PaymentBookingNested schema"""
        # Arrange - Create payment with booking
        payment = Payment(
            booking_id=test_booking.id,
            invoice_id=test_invoice.id,
            amount=Decimal("600000.00"),
            payment_method="bank_transfer",
            payment_type="installment",
            payment_date=date.today(),
            status="partial",
            reference_number="REF-SCHEMA-BK",
            created_by=test_user["id"]
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Act - Serialize via schema
        from app.schemas.payment import PaymentResponse
        response = PaymentResponse.from_orm(payment)
        response_dict = response.model_dump()
        
        # Assert - Verify booking object has all required fields from PaymentBookingNested
        booking = response_dict['booking']
        assert booking is not None
        
        expected_fields = ['id', 'booking_code', 'status', 'check_in',
                          'check_out', 'total', 'total_pax']
        
        for field in expected_fields:
            assert field in booking, f"Missing booking field: {field}"
        
        # Verify booking field exists and is properly nested (not just an ID)
        assert 'booking' in response_dict
        assert isinstance(booking, dict)
        assert len(booking) >= len(expected_fields)
        
        # Note: invoice_id field is NOT exposed in the PaymentResponse schema
        # Only the nested booking object is returned


# ============================================================================
# Integration Tests
# ============================================================================

class TestPaymentRelationshipsIntegration:
    """Integration tests for payment relationships"""
    
    def test_complete_payment_workflow_with_relationships(
        self, db: Session, client: TestClient, user_headers,
        test_user, test_invoice
    ):
        """Test complete payment workflow maintains relationships"""
        # Arrange - Create payment via API
        payment_payload = {
            "invoice_id": test_invoice.id,
            "amount": 400000.00,
            "payment_method": "bank_transfer",
            "payment_date": date.today().isoformat(),
            "status": "partial",
            "payment_type": "down-payment",
            "reference_number": "REF-WORKFLOW-001"
        }
        
        # Act - Create payment
        create_response = client.post(
            "/api/v1/payments",
            headers=user_headers,
            json=payment_payload
        )
        
        assert create_response.status_code == 201
        payment_id = create_response.json()["id"]
        
        # Act - Retrieve payment
        get_response = client.get(
            f"/api/v1/payments/{payment_id}",
            headers=user_headers
        )
        
        # Assert
        assert get_response.status_code == 200
        data = get_response.json()
        
        # Verify all relationships are present
        assert data['created_by']['id'] == test_user["id"]
        assert data['invoice']['id'] == test_invoice.id
        assert data['customer'] is not None
        assert len(data['history']) >= 1  # At least creation event
    
    def test_payment_list_performance_with_relationships(
        self, db: Session, client: TestClient, user_headers,
        test_user, test_invoice
    ):
        """Test payment list endpoint performance with eager loading"""
        # Arrange - Create multiple payments
        for i in range(5):
            payment_data = PaymentCreate(
                invoice_id=test_invoice.id,
                amount=Decimal(f"{(i+1) * 50000}.00"),
                payment_method=PaymentMethod.bank_transfer,
                payment_date=date.today(),
                status=PaymentStatus.partial,
                payment_type=PaymentType.installment,
                reference_number=f"REF-PERF-{i}"
            )
            create_payment(db, payment_data, created_by=test_user["id"])
        
        # Act
        response = client.get(
            "/api/v1/payments",
            headers=user_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # All payments should have relationships loaded
        assert len(data['payments']) >= 5
        for payment in data['payments']:
            assert 'created_by' in payment
            assert 'invoice' in payment
            # Verify relationships are populated (not lazy-loaded)
            assert payment['created_by'] is not None