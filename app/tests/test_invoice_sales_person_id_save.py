"""
Unit test to verify that sales_person_id is correctly saved when creating an invoice.

This test validates the fix where the sales_person_id field from the request payload
is properly persisted to the invoices table.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.payment import Invoice, InvoiceItem
from app.schemas.payment import InvoiceCreate, InvoiceItemCreate


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_sales_person(db: Session) -> User:
    """Create a test sales person user"""
    sales_person = User(
        username="sales_person_test",
        email="salesperson@test.com",
        full_name="Test Sales Person",
        password_hash="hashed_password_test",
        role="sales",
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(sales_person)
    db.commit()
    db.refresh(sales_person)
    return sales_person


@pytest.fixture
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer for invoice creation"""
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
def test_package(db: Session, test_user) -> Package:
    """Create a test package for invoice items"""
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        category="Adventure",
        type="Tour",
        description="Test package description",
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
    """Create a test villa for invoice"""
    villa = Villa(
        name="Villa Paradise",
        description="Test villa",
        base_price=Decimal("1000000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# Unit Tests - Direct Database Validation
# ============================================================================

class TestInvoiceSalesPersonIdSave:
    """Test that sales_person_id is correctly saved when creating an invoice"""
    
    def test_invoice_creation_with_sales_person_id(
        self, 
        db: Session, 
        test_user, 
        test_sales_person,
        test_customer, 
        test_package,
        test_villa
    ):
        """
        Test creating invoice with sales_person_id field.
        Validates that sales_person_id is properly saved to the invoices table.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice data with sales_person_id
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            sales_person_id=test_sales_person.id,  # Include sales_person_id
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("45000000.00"),
            tax_total=Decimal("0.00"),
            payment_terms="Net 30",
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 2),
            villa_ids=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        
        # Act - Import and call create_invoice service
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice was created successfully
        assert invoice is not None
        assert invoice.id is not None
        assert invoice.invoice_number is not None
        
        # Assert - Verify sales_person_id was saved
        assert invoice.sales_person_id is not None, "sales_person_id should not be None"
        assert invoice.sales_person_id == test_sales_person.id, \
            f"Expected sales_person_id to be {test_sales_person.id}, but got {invoice.sales_person_id}"
        
        # Assert - Verify sales_person_id in database using direct query
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        assert db_invoice is not None
        assert db_invoice.sales_person_id == test_sales_person.id, \
            f"Database record has incorrect sales_person_id. Expected {test_sales_person.id}, got {db_invoice.sales_person_id}"
        
        # Assert - Verify the sales_person relationship works
        assert db_invoice.sales_person is not None, "sales_person relationship should be accessible"
        assert db_invoice.sales_person.id == test_sales_person.id
        assert db_invoice.sales_person.username == "sales_person_test"
    
    
    def test_invoice_creation_without_sales_person_id(
        self, 
        db: Session, 
        test_user, 
        test_customer, 
        test_package,
        test_villa
    ):
        """
        Test creating invoice without sales_person_id field.
        Validates that sales_person_id can be None (optional field).
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice data without sales_person_id
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            # sales_person_id is intentionally omitted (should default to None)
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("300000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("300000.00")
                )
            ]
        )
        
        # Act
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice created successfully
        assert invoice is not None
        assert invoice.id is not None
        
        # Assert - sales_person_id should be None
        assert invoice.sales_person_id is None, \
            f"sales_person_id should be None when not provided, but got {invoice.sales_person_id}"
        
        # Assert - Verify in database
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        assert db_invoice.sales_person_id is None
    
    
    def test_invoice_creation_with_different_sales_persons(
        self, 
        db: Session, 
        test_user, 
        test_sales_person,
        test_customer, 
        test_package,
        test_villa
    ):
        """
        Test creating multiple invoices with different sales_person_ids.
        Validates that each invoice correctly stores its respective sales_person_id.
        """
        # Arrange - Create another sales person
        sales_person_2 = User(
            username="sales_person_2",
            email="salesperson2@test.com",
            full_name="Second Sales Person",
            password_hash="hashed_password_test",
            role="sales",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(sales_person_2)
        db.commit()
        db.refresh(sales_person_2)
        
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create first invoice with first sales person
        invoice_data_1 = InvoiceCreate(
            customer_id=test_customer.id,
            sales_person_id=test_sales_person.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("400000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("400000.00")
                )
            ]
        )
        
        # Create second invoice with second sales person
        invoice_data_2 = InvoiceCreate(
            customer_id=test_customer.id,
            sales_person_id=sales_person_2.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("600000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("600000.00")
                )
            ]
        )
        
        # Act
        from app.services.payment import create_invoice
        invoice_1 = create_invoice(db, invoice_data_1, user_obj)
        invoice_2 = create_invoice(db, invoice_data_2, user_obj)
        
        # Assert - Both invoices created successfully
        assert invoice_1 is not None
        assert invoice_2 is not None
        
        # Assert - Each invoice has correct sales_person_id
        assert invoice_1.sales_person_id == test_sales_person.id
        assert invoice_2.sales_person_id == sales_person_2.id
        
        # Assert - Verify different sales_person_ids
        assert invoice_1.sales_person_id != invoice_2.sales_person_id, \
            "Different invoices should have different sales_person_ids"
        
        # Assert - Verify in database
        db_invoice_1 = db.query(Invoice).filter(Invoice.id == invoice_1.id).first()
        db_invoice_2 = db.query(Invoice).filter(Invoice.id == invoice_2.id).first()
        
        assert db_invoice_1.sales_person_id == test_sales_person.id
        assert db_invoice_2.sales_person_id == sales_person_2.id
        
        # Assert - Verify relationships point to correct users
        assert db_invoice_1.sales_person.username == "sales_person_test"
        assert db_invoice_2.sales_person.username == "sales_person_2"
    
    
    def test_invoice_with_sales_person_id_matches_frontend_payload(
        self, 
        db: Session, 
        test_user, 
        test_sales_person,
        test_customer, 
        test_package,
        test_villa
    ):
        """
        Test creating invoice with the exact payload structure from the frontend example.
        This mimics the real-world scenario described in the bug report.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Exact payload structure from bug report (simplified for test)
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date(2026, 1, 19),
            due_date=date(2026, 2, 18),
            status="draft",
            total=Decimal("45000000.00"),
            tax_total=Decimal("0.00"),
            payment_terms="Net 30",
            sales_person_id=6,  # This is what frontend sends
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 2),
            villa_ids=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("45000000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("45000000.00")
                )
            ]
        )
        
        # Act
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice was created
        assert invoice is not None
        
        # Assert - sales_person_id was saved exactly as sent from frontend
        assert invoice.sales_person_id == 6, \
            f"sales_person_id should be 6 as sent from frontend, but got {invoice.sales_person_id}"
        
        # Assert - Verify in database
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        assert db_invoice.sales_person_id == 6, \
            "sales_person_id not persisted to database correctly"
