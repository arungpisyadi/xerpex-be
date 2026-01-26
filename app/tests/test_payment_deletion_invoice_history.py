"""
Unit tests for payment deletion and invoice history cleanup

Tests verify that when a payment is deleted, related invoice_history records are also deleted.
This ensures data integrity and prevents orphaned history records.
"""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import HTTPException

from app.models.payment import Payment, Invoice, InvoiceItem, InvoiceHistory
from app.models.customer import Customer
from app.models.package import Package
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentMethod, PaymentType, PaymentStatus
from app.services.payment import create_payment, delete_payment


@pytest.fixture
def setup_test_data(db):
    """Setup test data for payment deletion tests"""
    # Create admin user (has permission to delete)
    admin_user = User(
        username="admin_test",
        email="admin@tugugroup.co.id",
        full_name="Admin User",
        password_hash="hashed_password",
        role="admin",
        phone="1234567890",
        is_active=True
    )
    db.add(admin_user)
    
    # Create finance user (has permission to delete)
    finance_user = User(
        username="finance_test",
        email="finance@test.com",
        full_name="Finance User",
        password_hash="hashed_password",
        role="finance",
        phone="1234567891",
        is_active=True
    )
    db.add(finance_user)
    
    # Create sales user (does NOT have permission to delete)
    sales_user = User(
        username="sales_test",
        email="sales@test.com",
        full_name="Sales User",
        password_hash="hashed_password",
        role="sales",
        phone="1234567892",
        is_active=True
    )
    db.add(sales_user)
    
    # Create customer
    customer = Customer(
        user_id=admin_user.id,
        name="Test Customer",
        email="customer@test.com",
        phone_number="9876543210",
        address="123 Test St",
        status="active"
    )
    db.add(customer)
    
    # Create package
    package = Package(
        user_id=admin_user.id,
        name="Test Package",
        description="Test package for testing",
        price=Decimal("100.00"),
        is_active=True
    )
    db.add(package)
    
    db.commit()
    db.refresh(admin_user)
    db.refresh(finance_user)
    db.refresh(sales_user)
    db.refresh(customer)
    db.refresh(package)
    
    # Create invoice
    invoice = Invoice(
        user_id=admin_user.id,
        customer_id=customer.id,
        invoice_number="INV-TEST-001",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal("100.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("100.00"),
        tax_total=Decimal("0.00")
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal("100.00"),
        discount=Decimal("0.00"),
        line_total=Decimal("100.00"),
        pax=1
    )
    db.add(invoice_item)
    db.commit()
    
    return {
        "admin_user": admin_user,
        "finance_user": finance_user,
        "sales_user": sales_user,
        "customer": customer,
        "package": package,
        "invoice": invoice
    }


def test_delete_payment_removes_invoice_history(db, setup_test_data):
    """Test that deleting a payment removes related invoice_history records"""
    admin_user = setup_test_data["admin_user"]
    invoice = setup_test_data["invoice"]
    
    # Create a payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("50.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="REF-001",
        status=PaymentStatus.completed,
        notes="Test payment"
    )
    
    payment = create_payment(db, payment_data, admin_user.id)
    payment_id = payment.id
    
    # Verify invoice_history records were created with payment_id
    history_records = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).all()
    
    assert len(history_records) > 0, "Invoice history records should be created when payment is added"
    
    # Delete the payment
    result = delete_payment(db, payment_id, admin_user.id)
    assert result is True, "Payment deletion should return True"
    
    # Verify payment was deleted
    deleted_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    assert deleted_payment is None, "Payment should be deleted"
    
    # Verify invoice_history records with payment_id were also deleted
    remaining_history = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).all()
    
    assert len(remaining_history) == 0, "Invoice history records with payment_id should be deleted"


def test_delete_payment_without_invoice_history(db, setup_test_data):
    """Test deleting a payment that has no invoice history works correctly"""
    admin_user = setup_test_data["admin_user"]
    invoice = setup_test_data["invoice"]
    
    # Create a payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("25.00"),
        payment_method=PaymentMethod.cash,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="REF-002",
        status=PaymentStatus.completed,
        notes="Test payment without history"
    )
    
    payment = create_payment(db, payment_data, admin_user.id)
    payment_id = payment.id
    
    # Manually delete all invoice history records for this payment (simulate edge case)
    db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).delete()
    db.commit()
    
    # Verify no invoice history exists
    history_count = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).count()
    assert history_count == 0, "No invoice history should exist"
    
    # Delete the payment - should not raise an error
    result = delete_payment(db, payment_id, admin_user.id)
    assert result is True, "Payment deletion should succeed even without history"
    
    # Verify payment was deleted
    deleted_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    assert deleted_payment is None, "Payment should be deleted"


def test_delete_payment_preserves_other_invoice_history(db, setup_test_data):
    """Test that deleting a payment only removes its own history records"""
    admin_user = setup_test_data["admin_user"]
    invoice = setup_test_data["invoice"]
    
    # Create first payment
    payment_data_1 = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("30.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="REF-003",
        status=PaymentStatus.completed,
        notes="First payment"
    )
    
    payment_1 = create_payment(db, payment_data_1, admin_user.id)
    payment_1_id = payment_1.id
    
    # Create second payment
    payment_data_2 = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("20.00"),
        payment_method=PaymentMethod.credit_card,
        payment_type=PaymentType.installment,
        payment_date=date.today(),
        reference_number="REF-004",
        status=PaymentStatus.completed,
        notes="Second payment"
    )
    
    payment_2 = create_payment(db, payment_data_2, admin_user.id)
    payment_2_id = payment_2.id
    
    # Verify both payments have invoice history
    history_payment_1 = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_1_id
    ).all()
    history_payment_2 = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_2_id
    ).all()
    
    assert len(history_payment_1) > 0, "Payment 1 should have history"
    assert len(history_payment_2) > 0, "Payment 2 should have history"
    
    payment_2_history_count = len(history_payment_2)
    
    # Delete first payment
    result = delete_payment(db, payment_1_id, admin_user.id)
    assert result is True, "Payment 1 deletion should succeed"
    
    # Verify payment 1 history is deleted
    remaining_history_1 = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_1_id
    ).all()
    assert len(remaining_history_1) == 0, "Payment 1 history should be deleted"
    
    # Verify payment 2 history is preserved
    remaining_history_2 = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_2_id
    ).all()
    assert len(remaining_history_2) == payment_2_history_count, "Payment 2 history should be preserved"


def test_delete_payment_permission_denied(db, setup_test_data):
    """Test that sales user cannot delete payment"""
    admin_user = setup_test_data["admin_user"]
    sales_user = setup_test_data["sales_user"]
    invoice = setup_test_data["invoice"]
    
    # Create a payment as admin
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("40.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="REF-005",
        status=PaymentStatus.completed,
        notes="Test payment"
    )
    
    payment = create_payment(db, payment_data, admin_user.id)
    payment_id = payment.id
    
    # Try to delete as sales user - should raise exception
    with pytest.raises(HTTPException) as exc_info:
        delete_payment(db, payment_id, sales_user.id)
    
    assert exc_info.value.status_code == 403, "Should return 403 Forbidden"
    assert "permission" in exc_info.value.detail.lower(), "Error message should mention permission"
    
    # Verify payment was NOT deleted
    payment_still_exists = db.query(Payment).filter(Payment.id == payment_id).first()
    assert payment_still_exists is not None, "Payment should still exist"
    
    # Verify invoice history was NOT deleted
    history_records = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).all()
    assert len(history_records) > 0, "Invoice history should still exist"


def test_finance_user_can_delete_payment(db, setup_test_data):
    """Test that finance user can delete payment and its history"""
    finance_user = setup_test_data["finance_user"]
    invoice = setup_test_data["invoice"]
    
    # Create a payment as finance user
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("60.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="REF-006",
        status=PaymentStatus.completed,
        notes="Finance payment"
    )
    
    payment = create_payment(db, payment_data, finance_user.id)
    payment_id = payment.id
    
    # Verify invoice history exists
    history_count = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).count()
    assert history_count > 0, "Invoice history should exist"
    
    # Delete payment as finance user
    result = delete_payment(db, payment_id, finance_user.id)
    assert result is True, "Finance user should be able to delete payment"
    
    # Verify payment was deleted
    deleted_payment = db.query(Payment).filter(Payment.id == payment_id).first()
    assert deleted_payment is None, "Payment should be deleted"
    
    # Verify invoice history was deleted
    history_count_after = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).count()
    assert history_count_after == 0, "Invoice history should be deleted"


def test_delete_nonexistent_payment(db, setup_test_data):
    """Test deleting a non-existent payment raises appropriate error"""
    admin_user = setup_test_data["admin_user"]
    
    # Try to delete non-existent payment
    with pytest.raises(HTTPException) as exc_info:
        delete_payment(db, 99999, admin_user.id)
    
    assert exc_info.value.status_code == 404, "Should return 404 Not Found"
    assert "not found" in exc_info.value.detail.lower(), "Error message should mention not found"


def test_invoice_history_without_payment_id_preserved(db, setup_test_data):
    """Test that invoice history records without payment_id are not affected"""
    admin_user = setup_test_data["admin_user"]
    invoice = setup_test_data["invoice"]
    
    # Create invoice history record WITHOUT payment_id (e.g., invoice status change)
    independent_history = InvoiceHistory(
        invoice_id=invoice.id,
        user_id=admin_user.id,
        payment_id=None,  # No payment_id
        event_type="status_changed",
        event_category="status",
        description="Invoice status changed to sent",
        event_metadata={"old_status": "draft", "new_status": "sent"},
        created_at=datetime.utcnow()
    )
    db.add(independent_history)
    db.commit()
    db.refresh(independent_history)
    
    # Create a payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal("50.00"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="REF-007",
        status=PaymentStatus.completed,
        notes="Test payment"
    )
    
    payment = create_payment(db, payment_data, admin_user.id)
    payment_id = payment.id
    
    # Delete the payment
    result = delete_payment(db, payment_id, admin_user.id)
    assert result is True, "Payment deletion should succeed"
    
    # Verify independent history record still exists
    independent_history_still_exists = db.query(InvoiceHistory).filter(
        InvoiceHistory.id == independent_history.id
    ).first()
    assert independent_history_still_exists is not None, "Independent history without payment_id should be preserved"
    
    # Verify payment history was deleted
    payment_history_deleted = db.query(InvoiceHistory).filter(
        InvoiceHistory.payment_id == payment_id
    ).count()
    assert payment_history_deleted == 0, "Payment-related history should be deleted"
