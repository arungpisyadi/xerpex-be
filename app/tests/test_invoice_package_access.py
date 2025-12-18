"""
Unit tests for package access control when creating/updating invoices.
Tests that privileged users (admin/finance/sales) can use ANY package in invoices,
while regular users can only use their own packages.
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
from app.services.payment import create_invoice, update_invoice
from app.schemas.payment import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, InvoiceStatus


@pytest.fixture(scope="function")
def setup_users_customers_and_packages(db: Session):
    """
    Setup test users with different roles, customers, and packages.
    Creates a comprehensive test environment for package access control.
    """
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
    regular_user_1 = User(
        email="user1@test.com",
        username="user1",
        password_hash="test",
        role="user",
        phone="1234567893"
    )
    regular_user_2 = User(
        email="user2@test.com",
        username="user2",
        password_hash="test",
        role="user",
        phone="1234567894"
    )
    
    db.add_all([admin_user, finance_user, sales_user, regular_user_1, regular_user_2])
    db.flush()
    
    # Create customers for each user
    customer_admin = Customer(
        user_id=admin_user.id,
        name="Admin Customer",
        email="customer.admin@test.com",
        phone_number="9876543210"
    )
    customer_finance = Customer(
        user_id=finance_user.id,
        name="Finance Customer",
        email="customer.finance@test.com",
        phone_number="9876543211"
    )
    customer_sales = Customer(
        user_id=sales_user.id,
        name="Sales Customer",
        email="customer.sales@test.com",
        phone_number="9876543212"
    )
    customer_user1 = Customer(
        user_id=regular_user_1.id,
        name="User1 Customer",
        email="customer.user1@test.com",
        phone_number="9876543213"
    )
    customer_user2 = Customer(
        user_id=regular_user_2.id,
        name="User2 Customer",
        email="customer.user2@test.com",
        phone_number="9876543214"
    )
    
    db.add_all([customer_admin, customer_finance, customer_sales, customer_user1, customer_user2])
    db.flush()
    
    # Create packages owned by different users
    package_admin = Package(
        user_id=admin_user.id,
        name="Admin Package",
        description="Package created by admin",
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
    )
    package_finance = Package(
        user_id=finance_user.id,
        name="Finance Package",
        description="Package created by finance",
        cost_per_pax=Decimal("150.00"),
        days=2,
        min_pax=1
    )
    package_sales = Package(
        user_id=sales_user.id,
        name="Sales Package",
        description="Package created by sales",
        cost_per_pax=Decimal("200.00"),
        days=3,
        min_pax=1
    )
    package_user1 = Package(
        user_id=regular_user_1.id,
        name="User1 Package",
        description="Package created by user1",
        cost_per_pax=Decimal("250.00"),
        days=4,
        min_pax=1
    )
    package_user2 = Package(
        user_id=regular_user_2.id,
        name="User2 Package",
        description="Package created by user2",
        cost_per_pax=Decimal("300.00"),
        days=5,
        min_pax=1
    )
    
    db.add_all([package_admin, package_finance, package_sales, package_user1, package_user2])
    db.commit()
    
    return {
        'admin_user': admin_user,
        'finance_user': finance_user,
        'sales_user': sales_user,
        'regular_user_1': regular_user_1,
        'regular_user_2': regular_user_2,
        'customer_admin': customer_admin,
        'customer_finance': customer_finance,
        'customer_sales': customer_sales,
        'customer_user1': customer_user1,
        'customer_user2': customer_user2,
        'package_admin': package_admin,
        'package_finance': package_finance,
        'package_sales': package_sales,
        'package_user1': package_user1,
        'package_user2': package_user2
    }


def test_admin_can_create_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that admin can create an invoice using a package created by any other user.
    This verifies the fix for package isolation in create_invoice.
    """
    data = setup_users_customers_and_packages
    admin_user = data['admin_user']
    customer_admin = data['customer_admin']
    package_user1 = data['package_user1']  # Package created by regular user
    
    # Admin creates an invoice using regular user's package
    invoice_data = InvoiceCreate(
        customer_id=customer_admin.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user1.id,
                unit_price=package_user1.cost_per_pax,
                discount=Decimal("0.00"),
                pax=2,
                line_total=package_user1.cost_per_pax * 2
            )
        ],
        villas=[]
    )
    
    # Should succeed - admin can access any package
    invoice = create_invoice(db, invoice_data, admin_user)
    
    assert invoice is not None
    assert invoice.user_id == admin_user.id
    assert len(invoice.items) == 1
    assert invoice.items[0].package_id == package_user1.id


def test_finance_can_create_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that finance user can create an invoice using a package created by any other user.
    Finance role should have access to all packages like admin.
    """
    data = setup_users_customers_and_packages
    finance_user = data['finance_user']
    customer_finance = data['customer_finance']
    package_user2 = data['package_user2']  # Package created by regular user
    
    # Finance creates an invoice using regular user's package
    invoice_data = InvoiceCreate(
        customer_id=customer_finance.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user2.id,
                unit_price=package_user2.cost_per_pax,
                discount=Decimal("0.00"),
                pax=3,
                line_total=package_user2.cost_per_pax * 3
            )
        ],
        villas=[]
    )
    
    # Should succeed - finance can access any package
    invoice = create_invoice(db, invoice_data, finance_user)
    
    assert invoice is not None
    assert invoice.user_id == finance_user.id
    assert len(invoice.items) == 1
    assert invoice.items[0].package_id == package_user2.id


def test_sales_can_create_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that sales user can create an invoice using a package created by any other user.
    Sales role should have access to all packages like admin and finance.
    """
    data = setup_users_customers_and_packages
    sales_user = data['sales_user']
    customer_sales = data['customer_sales']
    package_admin = data['package_admin']  # Package created by admin
    
    # Sales creates an invoice using admin's package
    invoice_data = InvoiceCreate(
        customer_id=customer_sales.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_admin.id,
                unit_price=package_admin.cost_per_pax,
                discount=Decimal("10.00"),
                pax=1,
                line_total=package_admin.cost_per_pax - Decimal("10.00")
            )
        ],
        villas=[]
    )
    
    # Should succeed - sales can access any package
    invoice = create_invoice(db, invoice_data, sales_user)
    
    assert invoice is not None
    assert invoice.user_id == sales_user.id
    assert len(invoice.items) == 1
    assert invoice.items[0].package_id == package_admin.id


def test_regular_user_cannot_create_invoice_with_other_users_package(db: Session, setup_users_customers_and_packages):
    """
    Test that regular (tenant) user cannot create an invoice using another user's package.
    This ensures proper isolation for regular users - they can only use their own packages.
    """
    data = setup_users_customers_and_packages
    regular_user_1 = data['regular_user_1']
    customer_user1 = data['customer_user1']
    package_user2 = data['package_user2']  # Package created by another regular user
    
    # Regular user tries to create an invoice using another user's package
    invoice_data = InvoiceCreate(
        customer_id=customer_user1.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user2.id,
                unit_price=package_user2.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user2.cost_per_pax
            )
        ],
        villas=[]
    )
    
    # Should fail with 404 - regular user cannot access another user's package
    with pytest.raises(HTTPException) as exc_info:
        create_invoice(db, invoice_data, regular_user_1)
    
    assert exc_info.value.status_code == 404
    assert "Package" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)


def test_regular_user_can_create_invoice_with_own_package(db: Session, setup_users_customers_and_packages):
    """
    Test that regular user can create an invoice using their own package.
    This verifies that the package access control doesn't break normal operation for users.
    """
    data = setup_users_customers_and_packages
    regular_user_1 = data['regular_user_1']
    customer_user1 = data['customer_user1']
    package_user1 = data['package_user1']  # Package created by same user
    
    # Regular user creates an invoice using their own package
    invoice_data = InvoiceCreate(
        customer_id=customer_user1.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user1.id,
                unit_price=package_user1.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user1.cost_per_pax
            )
        ],
        villas=[]
    )
    
    # Should succeed - user can access their own package
    invoice = create_invoice(db, invoice_data, regular_user_1)
    
    assert invoice is not None
    assert invoice.user_id == regular_user_1.id
    assert len(invoice.items) == 1
    assert invoice.items[0].package_id == package_user1.id


def test_admin_can_update_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that admin can update an invoice to use a package created by any other user.
    This verifies the fix for package isolation in update_invoice.
    """
    data = setup_users_customers_and_packages
    admin_user = data['admin_user']
    customer_admin = data['customer_admin']
    package_admin = data['package_admin']
    package_user1 = data['package_user1']
    
    # First create an invoice with admin's own package
    invoice_data = InvoiceCreate(
        customer_id=customer_admin.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_admin.id,
                unit_price=package_admin.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_admin.cost_per_pax
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, admin_user)
    
    # Now update the invoice to use regular user's package
    update_data = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package_user1.id,
                unit_price=package_user1.cost_per_pax,
                discount=Decimal("5.00"),
                pax=2,
                line_total=(package_user1.cost_per_pax * 2) - Decimal("5.00")
            )
        ],
        villas=[]
    )
    
    # Should succeed - admin can update to use any package
    updated_invoice = update_invoice(db, invoice.id, update_data, admin_user.id)
    
    assert updated_invoice is not None
    assert len(updated_invoice.items) == 1
    assert updated_invoice.items[0].package_id == package_user1.id


def test_finance_can_update_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that finance user can update an invoice to use a package created by any other user.
    Finance role should have access to all packages in updates.
    """
    data = setup_users_customers_and_packages
    finance_user = data['finance_user']
    customer_finance = data['customer_finance']
    package_finance = data['package_finance']
    package_sales = data['package_sales']
    
    # First create an invoice with finance's own package
    invoice_data = InvoiceCreate(
        customer_id=customer_finance.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_finance.id,
                unit_price=package_finance.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_finance.cost_per_pax
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, finance_user)
    
    # Now update the invoice to use sales user's package
    update_data = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package_sales.id,
                unit_price=package_sales.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_sales.cost_per_pax
            )
        ],
        villas=[]
    )
    
    # Should succeed - finance can update to use any package
    updated_invoice = update_invoice(db, invoice.id, update_data, finance_user.id)
    
    assert updated_invoice is not None
    assert len(updated_invoice.items) == 1
    assert updated_invoice.items[0].package_id == package_sales.id


def test_sales_can_update_invoice_with_any_package(db: Session, setup_users_customers_and_packages):
    """
    Test that sales user can update an invoice to use a package created by any other user.
    Sales role should have access to all packages in updates.
    """
    data = setup_users_customers_and_packages
    sales_user = data['sales_user']
    customer_sales = data['customer_sales']
    package_sales = data['package_sales']
    package_finance = data['package_finance']
    
    # First create an invoice with sales's own package
    invoice_data = InvoiceCreate(
        customer_id=customer_sales.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_sales.id,
                unit_price=package_sales.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_sales.cost_per_pax
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, sales_user)
    
    # Now update the invoice to use finance user's package
    update_data = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package_finance.id,
                unit_price=package_finance.cost_per_pax,
                discount=Decimal("20.00"),
                pax=3,
                line_total=(package_finance.cost_per_pax * 3) - Decimal("20.00")
            )
        ],
        villas=[]
    )
    
    # Should succeed - sales can update to use any package
    updated_invoice = update_invoice(db, invoice.id, update_data, sales_user.id)
    
    assert updated_invoice is not None
    assert len(updated_invoice.items) == 1
    assert updated_invoice.items[0].package_id == package_finance.id


def test_regular_user_cannot_update_invoice_with_other_users_package(db: Session, setup_users_customers_and_packages):
    """
    Test that regular user cannot update an invoice to use another user's package.
    This ensures proper isolation for regular users in invoice updates.
    """
    data = setup_users_customers_and_packages
    regular_user_1 = data['regular_user_1']
    customer_user1 = data['customer_user1']
    package_user1 = data['package_user1']
    package_user2 = data['package_user2']
    
    # First create an invoice with user1's own package
    invoice_data = InvoiceCreate(
        customer_id=customer_user1.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user1.id,
                unit_price=package_user1.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user1.cost_per_pax
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, regular_user_1)
    
    # Now try to update the invoice to use another user's package
    update_data = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package_user2.id,
                unit_price=package_user2.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user2.cost_per_pax
            )
        ],
        villas=[]
    )
    
    # Should fail with 404 - regular user cannot access another user's package
    with pytest.raises(HTTPException) as exc_info:
        update_invoice(db, invoice.id, update_data, regular_user_1.id)
    
    assert exc_info.value.status_code == 404
    assert "Package" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)


def test_regular_user_can_update_invoice_with_own_package(db: Session, setup_users_customers_and_packages):
    """
    Test that regular user can update an invoice using their own packages.
    This verifies that normal update operations work correctly for users.
    """
    data = setup_users_customers_and_packages
    regular_user_2 = data['regular_user_2']
    customer_user2 = data['customer_user2']
    package_user2 = data['package_user2']
    
    # Create another package for the same user
    package_user2_extra = Package(
        user_id=regular_user_2.id,
        name="User2 Extra Package",
        description="Another package by user2",
        cost_per_pax=Decimal("350.00"),
        days=6,
        min_pax=1
    )
    db.add(package_user2_extra)
    db.commit()
    
    # First create an invoice with one of user2's packages
    invoice_data = InvoiceCreate(
        customer_id=customer_user2.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user2.id,
                unit_price=package_user2.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user2.cost_per_pax
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, regular_user_2)
    
    # Now update the invoice to use another of user2's own packages
    update_data = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package_user2_extra.id,
                unit_price=package_user2_extra.cost_per_pax,
                discount=Decimal("50.00"),
                pax=2,
                line_total=(package_user2_extra.cost_per_pax * 2) - Decimal("50.00")
            )
        ],
        villas=[]
    )
    
    # Should succeed - user can update to use their own package
    updated_invoice = update_invoice(db, invoice.id, update_data, regular_user_2.id)
    
    assert updated_invoice is not None
    assert len(updated_invoice.items) == 1
    assert updated_invoice.items[0].package_id == package_user2_extra.id


def test_admin_can_use_multiple_packages_from_different_users(db: Session, setup_users_customers_and_packages):
    """
    Test that admin can create an invoice with multiple items using packages from different users.
    This tests the comprehensive package access for privileged users.
    """
    data = setup_users_customers_and_packages
    admin_user = data['admin_user']
    customer_admin = data['customer_admin']
    package_user1 = data['package_user1']
    package_user2 = data['package_user2']
    package_sales = data['package_sales']
    
    # Admin creates an invoice with packages from multiple different users
    invoice_data = InvoiceCreate(
        customer_id=customer_admin.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=package_user1.id,
                unit_price=package_user1.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_user1.cost_per_pax
            ),
            InvoiceItemCreate(
                package_id=package_user2.id,
                unit_price=package_user2.cost_per_pax,
                discount=Decimal("10.00"),
                pax=2,
                line_total=(package_user2.cost_per_pax * 2) - Decimal("10.00")
            ),
            InvoiceItemCreate(
                package_id=package_sales.id,
                unit_price=package_sales.cost_per_pax,
                discount=Decimal("0.00"),
                pax=1,
                line_total=package_sales.cost_per_pax
            )
        ],
        villas=[]
    )
    
    # Should succeed - admin can access packages from all users
    invoice = create_invoice(db, invoice_data, admin_user)
    
    assert invoice is not None
    assert invoice.user_id == admin_user.id
    assert len(invoice.items) == 3
    # Verify all packages are included
    package_ids = [item.package_id for item in invoice.items]
    assert package_user1.id in package_ids
    assert package_user2.id in package_ids
    assert package_sales.id in package_ids


def test_nonexistent_package_raises_404_for_all_users(db: Session, setup_users_customers_and_packages):
    """
    Test that trying to use a non-existent package raises 404 for all users regardless of role.
    This ensures consistent error handling for invalid package IDs.
    """
    data = setup_users_customers_and_packages
    admin_user = data['admin_user']
    customer_admin = data['customer_admin']
    
    # Try to create an invoice with non-existent package ID
    invoice_data = InvoiceCreate(
        customer_id=customer_admin.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status=InvoiceStatus.draft,
        items=[
            InvoiceItemCreate(
                package_id=99999,  # Non-existent package ID
                unit_price=Decimal("100.00"),
                discount=Decimal("0.00"),
                pax=1,
                line_total=Decimal("100.00")
            )
        ],
        villas=[]
    )
    
    # Should fail with 404 - package doesn't exist
    with pytest.raises(HTTPException) as exc_info:
        create_invoice(db, invoice_data, admin_user)
    
    assert exc_info.value.status_code == 404
    assert "Package" in str(exc_info.value.detail)
    assert "not found" in str(exc_info.value.detail)
