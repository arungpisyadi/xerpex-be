"""
Unit tests for invoice delete permissions
Tests that only admin and finance roles can delete invoices, not sales
"""
import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.payment import Invoice, InvoiceItem
from app.models.package import Package
from app.services.payment import create_invoice, delete_invoice
from app.schemas.payment import InvoiceCreate, InvoiceItemCreate, InvoiceStatus
from app.utils.security import has_delete_permission


def test_has_delete_permission_admin():
    """Test that admin has delete permission"""
    admin_user = User(
        id=1,
        username="admin",
        email="admin@example.com",
        role="admin",
        is_active=True
    )
    assert has_delete_permission(admin_user) == True


def test_has_delete_permission_finance():
    """Test that finance has delete permission"""
    finance_user = User(
        id=2,
        username="finance",
        email="finance@example.com",
        role="finance",
        is_active=True
    )
    assert has_delete_permission(finance_user) == True


def test_has_delete_permission_sales():
    """Test that sales does NOT have delete permission"""
    sales_user = User(
        id=3,
        username="sales",
        email="sales@example.com",
        role="sales",
        is_active=True
    )
    assert has_delete_permission(sales_user) == False


def test_has_delete_permission_other_roles():
    """Test that other roles do NOT have delete permission"""
    other_user = User(
        id=4,
        username="other",
        email="other@example.com",
        role="other",
        is_active=True
    )
    assert has_delete_permission(other_user) == False


def test_admin_can_delete_draft_invoice(db: Session):
    """Test that admin user can delete draft invoices"""
    # Create admin user
    admin_user = User(
        username="admin_delete",
        email="admin_delete@example.com",
        password_hash="hashed_password",
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # Create customer
    customer = Customer(
        user_id=admin_user.id,
        name="Test Customer",
        email="customer@example.com",
        phone_number="+621234567890"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create package
    package = Package(
        user_id=admin_user.id,
        name="Test Package",
        description="Test Description",
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a draft invoice
    invoice_create = InvoiceCreate(
        customer_id=customer.id,
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                line_total=Decimal("100.00"),
                pax=1
            )
        ],
        villas=[],
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today(),
        check_out=date.today() + timedelta(days=2),
        status=InvoiceStatus.draft,
        sales_person_id=None
    )
    
    invoice = create_invoice(db, invoice_create, admin_user)
    invoice_id = invoice.id
    
    # Admin should be able to delete the invoice
    result = delete_invoice(db, invoice_id, admin_user.id)
    assert result == True
    
    # Verify invoice is deleted
    deleted_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    assert deleted_invoice is None


def test_finance_can_delete_draft_invoice(db: Session):
    """Test that finance user can delete draft invoices"""
    # Create finance user
    finance_user = User(
        username="finance_delete",
        email="finance_delete@example.com",
        password_hash="hashed_password",
        role="finance",
        is_active=True
    )
    db.add(finance_user)
    db.commit()
    db.refresh(finance_user)
    
    # Create customer
    customer = Customer(
        user_id=finance_user.id,
        name="Test Customer",
        email="customer@example.com",
        phone_number="+621234567890"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create package
    package = Package(
        user_id=finance_user.id,
        name="Test Package",
        description="Test Description",
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a draft invoice
    invoice_create = InvoiceCreate(
        customer_id=customer.id,
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                line_total=Decimal("100.00"),
                pax=1
            )
        ],
        villas=[],
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today(),
        check_out=date.today() + timedelta(days=2),
        status=InvoiceStatus.draft,
        sales_person_id=None
    )
    
    invoice = create_invoice(db, invoice_create, finance_user)
    invoice_id = invoice.id
    
    # Finance should be able to delete the invoice
    result = delete_invoice(db, invoice_id, finance_user.id)
    assert result == True
    
    # Verify invoice is deleted
    deleted_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    assert deleted_invoice is None


def test_sales_cannot_delete_draft_invoice(db: Session):
    """Test that sales user CANNOT delete draft invoices"""
    # Create sales user
    sales_user = User(
        username="sales_delete",
        email="sales_delete@example.com",
        password_hash="hashed_password",
        role="sales",
        is_active=True
    )
    db.add(sales_user)
    db.commit()
    db.refresh(sales_user)
    
    # Create customer
    customer = Customer(
        user_id=sales_user.id,
        name="Test Customer",
        email="customer@example.com",
        phone_number="+621234567890"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create package
    package = Package(
        user_id=sales_user.id,
        name="Test Package",
        description="Test Description",
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a draft invoice
    invoice_create = InvoiceCreate(
        customer_id=customer.id,
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                line_total=Decimal("100.00"),
                pax=1
            )
        ],
        villas=[],
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today(),
        check_out=date.today() + timedelta(days=2),
        status=InvoiceStatus.draft,
        sales_person_id=None
    )
    
    invoice = create_invoice(db, invoice_create, sales_user)
    invoice_id = invoice.id
    
    # Sales should NOT be able to delete the invoice - should raise HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        delete_invoice(db, invoice_id, sales_user.id)
    
    assert exc_info.value.status_code == 403
    assert "do not have permission to delete" in exc_info.value.detail.lower()
    
    # Verify invoice still exists
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    assert invoice is not None
    assert invoice.status == "draft"
