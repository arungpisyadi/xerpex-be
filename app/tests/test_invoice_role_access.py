"""
Unit tests for invoice role-based access control fix.
Tests that privileged users (admin/finance/sales) can access invoices created by others,
while regular users maintain proper isolation.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.payment import Invoice, InvoiceItem
from app.models.package import Package
from app.services.payment import (
    update_invoice_status,
    update_invoice,
    update_invoice_notes,
    delete_invoice,
    get_invoice
)
from app.schemas.payment import (
    InvoiceStatusUpdate,
    InvoiceUpdate,
    InvoiceNotesUpdate,
    InvoiceStatus
)


@pytest.fixture
def setup_users_and_invoice(db: Session):
    """Setup test users and a sample invoice."""
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
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
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
        status="draft",
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
    db.commit()
    
    return {
        'admin_user': admin_user,
        'finance_user': finance_user,
        'sales_user': sales_user,
        'regular_user': regular_user,
        'other_regular_user': other_regular_user,
        'invoice': invoice,
        'customer': customer,
        'package': package
    }


def test_admin_can_update_invoice_status_from_other_user(db: Session, setup_users_and_invoice):
    """Test that admin can update invoice status for invoices created by other users."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    admin_user = data['admin_user']
    
    # Admin should be able to update the invoice status
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    updated_invoice = update_invoice_status(
        db=db,
        invoice_id=invoice.id,
        status_update=status_update,
        user_id=admin_user.id
    )
    
    assert updated_invoice is not None
    assert updated_invoice.status == "sent"


def test_finance_can_update_invoice_status_from_other_user(db: Session, setup_users_and_invoice):
    """Test that finance user can update invoice status for invoices created by other users."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    finance_user = data['finance_user']
    
    # Finance should be able to update the invoice status
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    updated_invoice = update_invoice_status(
        db=db,
        invoice_id=invoice.id,
        status_update=status_update,
        user_id=finance_user.id
    )
    
    assert updated_invoice is not None
    assert updated_invoice.status == "sent"


def test_sales_can_update_invoice_status_from_other_user(db: Session, setup_users_and_invoice):
    """Test that sales user can update invoice status for invoices created by other users."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    sales_user = data['sales_user']
    
    # Sales should be able to update the invoice status
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    updated_invoice = update_invoice_status(
        db=db,
        invoice_id=invoice.id,
        status_update=status_update,
        user_id=sales_user.id
    )
    
    assert updated_invoice is not None
    assert updated_invoice.status == "sent"


def test_regular_user_cannot_update_other_users_invoice(db: Session, setup_users_and_invoice):
    """Test that regular users maintain proper isolation and cannot access other users' invoices."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    other_regular_user = data['other_regular_user']
    
    # Other regular user should NOT be able to update the invoice
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    
    with pytest.raises(HTTPException) as exc_info:
        update_invoice_status(
            db=db,
            invoice_id=invoice.id,
            status_update=status_update,
            user_id=other_regular_user.id
        )
    
    assert exc_info.value.status_code == 404
    assert "Invoice not found" in str(exc_info.value.detail)


def test_regular_user_can_update_own_invoice(db: Session, setup_users_and_invoice):
    """Test that regular users can update their own invoices."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    regular_user = data['regular_user']
    
    # Owner should be able to update their own invoice
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    updated_invoice = update_invoice_status(
        db=db,
        invoice_id=invoice.id,
        status_update=status_update,
        user_id=regular_user.id
    )
    
    assert updated_invoice is not None
    assert updated_invoice.status == "sent"


def test_admin_can_update_invoice_notes(db: Session, setup_users_and_invoice):
    """Test that admin can update invoice notes for invoices created by other users."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    admin_user = data['admin_user']
    
    notes_update = InvoiceNotesUpdate(notes="Updated by admin")
    updated_invoice = update_invoice_notes(
        db=db,
        invoice_id=invoice.id,
        notes_update=notes_update,
        user_id=admin_user.id
    )
    
    assert updated_invoice is not None
    assert updated_invoice.notes == "Updated by admin"


def test_admin_can_get_invoice_from_other_user(db: Session, setup_users_and_invoice):
    """Test that admin can retrieve invoices created by other users using get_invoice."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    admin_user = data['admin_user']
    
    # Admin should be able to get the invoice
    retrieved_invoice = get_invoice(db=db, invoice_id=invoice.id, current_user=admin_user)
    
    assert retrieved_invoice is not None
    assert retrieved_invoice.id == invoice.id


def test_regular_user_cannot_get_other_users_invoice(db: Session, setup_users_and_invoice):
    """Test that regular users cannot retrieve other users' invoices using get_invoice."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    other_regular_user = data['other_regular_user']
    
    # Other regular user should NOT be able to get the invoice
    retrieved_invoice = get_invoice(db=db, invoice_id=invoice.id, current_user=other_regular_user)
    
    assert retrieved_invoice is None


def test_delete_invoice_admin_can_delete_draft_from_other_user(db: Session, setup_users_and_invoice):
    """Test that admin can delete draft invoices created by other users."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    admin_user = data['admin_user']
    
    # Ensure invoice is in draft status
    assert invoice.status == "draft"
    
    # Admin should be able to delete the draft invoice
    result = delete_invoice(db=db, invoice_id=invoice.id, user_id=admin_user.id)
    
    assert result is True
    
    # Verify invoice is deleted
    deleted_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
    assert deleted_invoice is None


def test_invoice_send_endpoint_scenario(db: Session, setup_users_and_invoice):
    """
    Test the actual invoice send endpoint scenario:
    Admin sending an invoice created by a regular user.
    This simulates the bug that was reported.
    """
    data = setup_users_and_invoice
    invoice = data['invoice']
    admin_user = data['admin_user']
    regular_user = data['regular_user']
    
    # Verify initial state
    assert invoice.user_id == regular_user.id
    assert invoice.status == "draft"
    
    # Admin tries to send the invoice (change status to 'sent')
    # This should NOT fail with 404 error
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    updated_invoice = update_invoice_status(
        db=db,
        invoice_id=invoice.id,
        status_update=status_update,
        user_id=admin_user.id
    )
    
    # Verify the invoice was successfully updated
    assert updated_invoice is not None
    assert updated_invoice.id == invoice.id
    assert updated_invoice.status == "sent"
    assert updated_invoice.user_id == regular_user.id  # Owner should remain the same


def test_nonexistent_user_raises_404(db: Session, setup_users_and_invoice):
    """Test that using a non-existent user ID raises 404."""
    data = setup_users_and_invoice
    invoice = data['invoice']
    
    status_update = InvoiceStatusUpdate(status=InvoiceStatus.sent)
    
    with pytest.raises(HTTPException) as exc_info:
        update_invoice_status(
            db=db,
            invoice_id=invoice.id,
            status_update=status_update,
            user_id=99999  # Non-existent user ID
        )
    
    assert exc_info.value.status_code == 404
    assert "User not found" in str(exc_info.value.detail)