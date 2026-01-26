"""
Unit tests for payment role-based access control fix.
Tests that privileged users (admin/finance/sales) can access payments created by others,
while regular users maintain proper isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.payment import Invoice, InvoiceItem, Payment
from app.models.package import Package
from app.services.payment import (
    update_payment,
    update_payment_status,
    delete_payment,
    get_payment
)
from app.schemas.payment import (
    PaymentUpdate,
    PaymentStatusUpdate,
    PaymentStatus,
    PaymentMethod
)


@pytest.fixture
def setup_users_and_payment(db: Session):
    """Setup test users and a sample payment."""
    # Create users with different roles
    admin_user = User(
        email="admin@test.com",
        username="admin",
        password_hash="test",
        role="admin",
        phone="1234567890"
    )
    finance_user = User(
        email="finance@test.com",
        username="finance",
        password_hash="test",
        role="finance",
        phone="1234567891"
    )
    sales_user = User(
        email="sales@test.com",
        username="sales",
        password_hash="test",
        role="sales",
        phone="1234567892"
    )
    regular_user = User(
        email="user@test.com",
        username="user",
        password_hash="test",
        role="user",
        phone="1234567893"
    )
    other_regular_user = User(
        email="user2@test.com",
        username="user2",
        password_hash="test",
        role="user",
        phone="1234567894"
    )
    
    db.add_all([admin_user, finance_user, sales_user, regular_user, other_regular_user])
    db.flush()
    
    # Create a customer owned by regular_user
    customer = Customer(
        user_id=regular_user.id,
        name="Test Customer",
        email="customer@test.com",
        phone_number="9876543210"
    )
    db.add(customer)
    db.flush()
    
    # Create a package owned by regular_user
    package = Package(
        user_id=regular_user.id,
        name="Test Package",
        description="Test package for invoice",
        price=Decimal("100.00")
    )
    db.add(package)
    db.flush()
    
    # Create an invoice owned by regular_user
    invoice = Invoice(
        user_id=regular_user.id,
        customer_id=customer.id,
        invoice_number="INV-TEST-001",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="sent",
        total=Decimal("100.00"),
        tax_total=Decimal("0.00")
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal("100.00"),
        discount=Decimal("0.00"),
        line_total=Decimal("100.00")
    )
    db.add(invoice_item)
    db.flush()
    
    # Create a payment created by regular_user
    payment = Payment(
        created_by=regular_user.id,
        invoice_id=invoice.id,
        amount=Decimal("50.00"),
        payment_method="bank_transfer",
        payment_date=date.today(),
        status="pending",
        reference_number="PAY-001"
    )
    db.add(payment)
    db.commit()
    
    return {
        'admin_user': admin_user,
        'finance_user': finance_user,
        'sales_user': sales_user,
        'regular_user': regular_user,
        'other_regular_user': other_regular_user,
        'invoice': invoice,
        'payment': payment,
        'customer': customer,
        'package': package
    }


def test_admin_can_update_payment_status_from_other_user(db: Session, setup_users_and_payment):
    """Test that admin can update payment status for payments created by other users."""
    data = setup_users_and_payment
    payment = data['payment']
    admin_user = data['admin_user']
    
    # Admin should be able to update the payment status
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    updated_payment = update_payment_status(
        db=db,
        payment_id=payment.id,
        status_update=status_update,
        created_by=admin_user.id
    )
    
    assert updated_payment is not None
    assert updated_payment.status == PaymentStatus.completed.value


def test_finance_can_update_payment_status_from_other_user(db: Session, setup_users_and_payment):
    """Test that finance user can update payment status for payments created by other users."""
    data = setup_users_and_payment
    payment = data['payment']
    finance_user = data['finance_user']
    
    # Finance should be able to update the payment status
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    updated_payment = update_payment_status(
        db=db,
        payment_id=payment.id,
        status_update=status_update,
        created_by=finance_user.id
    )
    
    assert updated_payment is not None
    assert updated_payment.status == PaymentStatus.completed.value


def test_sales_can_update_payment_status_from_other_user(db: Session, setup_users_and_payment):
    """Test that sales user can update payment status for payments created by other users."""
    data = setup_users_and_payment
    payment = data['payment']
    sales_user = data['sales_user']
    
    # Sales should be able to update the payment status
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    updated_payment = update_payment_status(
        db=db,
        payment_id=payment.id,
        status_update=status_update,
        created_by=sales_user.id
    )
    
    assert updated_payment is not None
    assert updated_payment.status == PaymentStatus.completed.value


def test_regular_user_cannot_update_other_users_payment(db: Session, setup_users_and_payment):
    """Test that regular users maintain proper isolation and cannot access other users' payments."""
    data = setup_users_and_payment
    payment = data['payment']
    other_regular_user = data['other_regular_user']
    
    # Other regular user should NOT be able to update the payment
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    
    with pytest.raises(HTTPException) as exc_info:
        update_payment_status(
            db=db,
            payment_id=payment.id,
            status_update=status_update,
            created_by=other_regular_user.id
        )
    
    assert exc_info.value.status_code == 404
    assert "Payment not found" in str(exc_info.value.detail)


def test_regular_user_can_update_own_payment(db: Session, setup_users_and_payment):
    """Test that regular users can update their own payments."""
    data = setup_users_and_payment
    payment = data['payment']
    regular_user = data['regular_user']
    
    # Owner should be able to update their own payment
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    updated_payment = update_payment_status(
        db=db,
        payment_id=payment.id,
        status_update=status_update,
        created_by=regular_user.id
    )
    
    assert updated_payment is not None
    assert updated_payment.status == PaymentStatus.completed.value


def test_admin_can_get_payment_from_other_user(db: Session, setup_users_and_payment):
    """Test that admin can retrieve payments created by other users using get_payment."""
    data = setup_users_and_payment
    payment = data['payment']
    admin_user = data['admin_user']
    
    # Admin should be able to get the payment
    retrieved_payment = get_payment(db=db, payment_id=payment.id, current_user=admin_user)
    
    assert retrieved_payment is not None
    assert retrieved_payment.id == payment.id


def test_regular_user_cannot_get_other_users_payment(db: Session, setup_users_and_payment):
    """Test that regular users cannot retrieve other users' payments using get_payment."""
    data = setup_users_and_payment
    payment = data['payment']
    other_regular_user = data['other_regular_user']
    
    # Other regular user should NOT be able to get the payment
    retrieved_payment = get_payment(db=db, payment_id=payment.id, current_user=other_regular_user)
    
    assert retrieved_payment is None


def test_admin_can_delete_payment_with_any_status(db: Session, setup_users_and_payment):
    """Test that admin can delete payments with any status created by other users."""
    data = setup_users_and_payment
    payment = data['payment']
    admin_user = data['admin_user']
    
    # Test deleting payment with pending status
    assert payment.status == "pending"
    
    # Admin should be able to delete the payment regardless of status
    result = delete_payment(db=db, payment_id=payment.id, created_by=admin_user.id)
    
    assert result is True
    
    # Verify payment is deleted
    deleted_payment = db.query(Payment).filter(Payment.id == payment.id).first()
    assert deleted_payment is None
    
    # Create another payment with completed status
    completed_payment = Payment(
        created_by=data['regular_user'].id,
        invoice_id=data['invoice'].id,
        amount=Decimal("75.00"),
        payment_method="bank_transfer",
        payment_date=date.today(),
        status="completed",
        reference_number="PAY-002"
    )
    db.add(completed_payment)
    db.commit()
    db.refresh(completed_payment)
    
    # Admin should be able to delete completed payment too
    result = delete_payment(db=db, payment_id=completed_payment.id, created_by=admin_user.id)
    assert result is True
    
    # Verify completed payment is deleted
    deleted_completed = db.query(Payment).filter(Payment.id == completed_payment.id).first()
    assert deleted_completed is None


def test_regular_user_cannot_delete_payment(db: Session, setup_users_and_payment):
    """Test that regular users without proper roles cannot delete payments."""
    data = setup_users_and_payment
    payment = data['payment']
    regular_user = data['regular_user']
    
    # Regular user should NOT be able to delete payment even if they created it
    with pytest.raises(HTTPException) as exc_info:
        delete_payment(db=db, payment_id=payment.id, created_by=regular_user.id)
    
    assert exc_info.value.status_code == 403
    assert "permission" in str(exc_info.value.detail).lower()


def test_finance_can_delete_payment_with_any_status(db: Session, setup_users_and_payment):
    """Test that finance users can delete payments with any status."""
    data = setup_users_and_payment
    invoice = data['invoice']
    finance_user = data['finance_user']
    
    # Create a completed payment
    completed_payment = Payment(
        created_by=data['regular_user'].id,
        invoice_id=invoice.id,
        amount=Decimal("60.00"),
        payment_method="credit_card",
        payment_date=date.today(),
        status="completed",
        reference_number="PAY-FIN-001"
    )
    db.add(completed_payment)
    db.commit()
    db.refresh(completed_payment)
    
    # Finance should be able to delete completed payment
    result = delete_payment(db=db, payment_id=completed_payment.id, created_by=finance_user.id)
    assert result is True
    
    # Verify payment is deleted
    deleted_payment = db.query(Payment).filter(Payment.id == completed_payment.id).first()
    assert deleted_payment is None


def test_admin_can_update_payment_details(db: Session, setup_users_and_payment):
    """Test that admin can update payment details for payments created by other users."""
    data = setup_users_and_payment
    payment = data['payment']
    admin_user = data['admin_user']
    
    payment_update = PaymentUpdate(
        amount=Decimal("50.00"),  # Keep the same amount
        reference_number="PAY-UPDATED",
        notes="Updated by admin"
    )
    updated_payment = update_payment(
        db=db,
        payment_id=payment.id,
        payment_update=payment_update,
        created_by=admin_user.id
    )
    
    assert updated_payment is not None
    assert updated_payment.reference_number == "PAY-UPDATED"
    assert updated_payment.notes == "Updated by admin"


def test_nonexistent_user_raises_404_for_payment(db: Session, setup_users_and_payment):
    """Test that using a non-existent user ID raises 404 for payment operations."""
    data = setup_users_and_payment
    payment = data['payment']
    
    status_update = PaymentStatusUpdate(status=PaymentStatus.completed)
    
    with pytest.raises(HTTPException) as exc_info:
        update_payment_status(
            db=db,
            payment_id=payment.id,
            status_update=status_update,
            created_by=99999  # Non-existent user ID
        )
    
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)