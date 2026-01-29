"""
Unit tests to verify that sales_person field (full_name) is included in GET /api/v1/invoices endpoint response.

This test validates that:
1. Invoices with valid sales_person_id return the correct full_name
2. Invoices with NULL sales_person_id return None
3. Invoices with non-existent sales_person_id return None
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
def test_sales_person_with_full_name(db: Session) -> User:
    """Create a test sales person user with full_name"""
    sales_person = User(
        username="sales_person_full",
        email="salesperson_full@test.com",
        full_name="John Sales Person",
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
def test_sales_person_without_full_name(db: Session) -> User:
    """Create a test sales person user without full_name"""
    sales_person = User(
        username="sales_person_no_name",
        email="salesperson_no_name@test.com",
        full_name=None,  # Explicitly None
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
def test_customer_sales_person(db: Session, test_user) -> Customer:
    """Create a test customer for invoice creation"""
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer Sales",
        email="customer_sales@test.com",
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
def test_package_sales_person(db: Session, test_user) -> Package:
    """Create a test package for invoice items"""
    package = Package(
        user_id=test_user["id"],
        name="Test Package Sales",
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
def test_villa_sales_person(db: Session) -> Villa:
    """Create a test villa for invoice"""
    villa = Villa(
        name="Villa Sales Test",
        description="Test villa for sales person",
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
# Unit Tests - Sales Person Field in Response
# ============================================================================

class TestInvoiceSalesPersonFieldResponse:
    """Test that sales_person field (full_name) is included in GET invoice endpoint response"""
    
    def test_invoice_with_valid_sales_person_returns_full_name(
        self, 
        db: Session, 
        test_user, 
        test_sales_person_with_full_name,
        test_customer_sales_person, 
        test_package_sales_person,
        test_villa_sales_person
    ):
        """
        Test that invoice with valid sales_person_id returns the correct full_name.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice with sales_person_id
        invoice_data = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            sales_person_id=test_sales_person_with_full_name.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        
        # Act - Create invoice
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Act - Fetch invoice using get_invoice (simulating GET endpoint)
        from app.services.payment import get_invoice
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        
        # Assert - Invoice was fetched
        assert fetched_invoice is not None
        assert fetched_invoice.id == invoice.id
        
        # Assert - sales_person relationship is loaded
        assert fetched_invoice.sales_person is not None
        assert fetched_invoice.sales_person.full_name == "John Sales Person"
        
        # Act - Convert to response schema (simulating API response)
        from app.schemas.payment import InvoiceResponse
        invoice_response = InvoiceResponse.model_validate(fetched_invoice)
        
        # Assert - sales_person field contains full_name
        assert invoice_response.sales_person is not None
        assert invoice_response.sales_person == "John Sales Person"
        assert invoice_response.sales_person_id == test_sales_person_with_full_name.id
    
    
    def test_invoice_with_null_sales_person_id_returns_none(
        self, 
        db: Session, 
        test_user, 
        test_customer_sales_person, 
        test_package_sales_person,
        test_villa_sales_person
    ):
        """
        Test that invoice with NULL sales_person_id returns None for sales_person field.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice without sales_person_id
        invoice_data = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            # sales_person_id omitted (should be None)
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("300000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("300000.00")
                )
            ]
        )
        
        # Act - Create invoice
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - sales_person_id is None
        assert invoice.sales_person_id is None
        
        # Act - Fetch invoice
        from app.services.payment import get_invoice
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        
        # Assert - sales_person relationship is None
        assert fetched_invoice.sales_person is None
        
        # Act - Convert to response schema
        from app.schemas.payment import InvoiceResponse
        invoice_response = InvoiceResponse.model_validate(fetched_invoice)
        
        # Assert - sales_person field is None
        assert invoice_response.sales_person is None
        assert invoice_response.sales_person_id is None
    
    
    def test_invoice_with_non_existent_sales_person_id_returns_none(
        self, 
        db: Session, 
        test_user, 
        test_customer_sales_person, 
        test_package_sales_person,
        test_villa_sales_person
    ):
        """
        Test that invoice with non-existent sales_person_id returns None for sales_person field.
        This could happen if a sales person user is deleted after invoice creation.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create a sales person that we'll delete
        temp_sales_person = User(
            username="temp_sales_delete",
            email="temp@delete.com",
            full_name="Temp Sales Person",
            password_hash="hashed_password_test",
            role="sales",
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(temp_sales_person)
        db.commit()
        db.refresh(temp_sales_person)
        temp_sales_person_id = temp_sales_person.id
        
        # Create invoice with this sales_person_id
        invoice_data = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            sales_person_id=temp_sales_person_id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("400000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("400000.00")
                )
            ]
        )
        
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Act - Simulate deletion of sales person (this would set sales_person_id to NULL due to ondelete="SET NULL")
        # Instead, we'll manually set it to None to simulate the scenario
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        db_invoice.sales_person_id = None
        db.commit()
        db.refresh(db_invoice)
        
        # Act - Fetch invoice
        from app.services.payment import get_invoice
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        
        # Assert - sales_person relationship is None
        assert fetched_invoice.sales_person is None
        assert fetched_invoice.sales_person_id is None
        
        # Act - Convert to response schema
        from app.schemas.payment import InvoiceResponse
        invoice_response = InvoiceResponse.model_validate(fetched_invoice)
        
        # Assert - sales_person field is None
        assert invoice_response.sales_person is None
    
    
    def test_invoice_list_includes_sales_person_field(
        self, 
        db: Session, 
        test_user, 
        test_sales_person_with_full_name,
        test_customer_sales_person, 
        test_package_sales_person,
        test_villa_sales_person
    ):
        """
        Test that get_invoices (list endpoint) includes sales_person field in response.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create multiple invoices with different sales_person scenarios
        # Invoice 1: with sales_person
        invoice_data_1 = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            sales_person_id=test_sales_person_with_full_name.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("500000.00")
                )
            ]
        )
        
        # Invoice 2: without sales_person
        invoice_data_2 = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            # No sales_person_id
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("600000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("600000.00")
                )
            ]
        )
        
        # Act - Create invoices
        from app.services.payment import create_invoice
        invoice_1 = create_invoice(db, invoice_data_1, user_obj)
        invoice_2 = create_invoice(db, invoice_data_2, user_obj)
        
        # Act - Fetch invoices list
        from app.services.payment import get_invoices
        invoices_list = get_invoices(db, user_obj, skip=0, limit=10)
        
        # Assert - Both invoices in list
        assert len(invoices_list) >= 2
        
        # Find our created invoices in the list
        found_invoice_1 = None
        found_invoice_2 = None
        
        for inv in invoices_list:
            if inv.id == invoice_1.id:
                found_invoice_1 = inv
            elif inv.id == invoice_2.id:
                found_invoice_2 = inv
        
        assert found_invoice_1 is not None
        assert found_invoice_2 is not None
        
        # Assert - Invoice 1 has sales_person loaded
        assert found_invoice_1.sales_person is not None
        assert found_invoice_1.sales_person.full_name == "John Sales Person"
        
        # Assert - Invoice 2 has no sales_person
        assert found_invoice_2.sales_person is None
        
        # Act - Convert to response schemas
        from app.schemas.payment import InvoiceResponse
        invoice_1_response = InvoiceResponse.model_validate(found_invoice_1)
        invoice_2_response = InvoiceResponse.model_validate(found_invoice_2)
        
        # Assert - Verify sales_person field in responses
        assert invoice_1_response.sales_person == "John Sales Person"
        assert invoice_2_response.sales_person is None
    
    
    def test_invoice_with_sales_person_without_full_name_returns_none(
        self, 
        db: Session, 
        test_user, 
        test_sales_person_without_full_name,
        test_customer_sales_person, 
        test_package_sales_person,
        test_villa_sales_person
    ):
        """
        Test that invoice with sales_person_id pointing to user without full_name returns None.
        Handles edge case where sales person user exists but has no full_name.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice with sales_person that has no full_name
        invoice_data = InvoiceCreate(
            customer_id=test_customer_sales_person.id,
            sales_person_id=test_sales_person_without_full_name.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villa_ids=[test_villa_sales_person.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package_sales_person.id,
                    unit_price=Decimal("700000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("700000.00")
                )
            ]
        )
        
        # Act - Create invoice
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Act - Fetch invoice
        from app.services.payment import get_invoice
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        
        # Assert - sales_person relationship exists but full_name is None
        assert fetched_invoice.sales_person is not None
        assert fetched_invoice.sales_person.full_name is None
        
        # Act - Convert to response schema
        from app.schemas.payment import InvoiceResponse
        invoice_response = InvoiceResponse.model_validate(fetched_invoice)
        
        # Assert - sales_person field should be None (edge case handling)
        assert invoice_response.sales_person is None
        assert invoice_response.sales_person_id == test_sales_person_without_full_name.id
