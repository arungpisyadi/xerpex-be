"""
Unit test to verify that villa_ids correctly save to invoice_villas table when creating a new invoice.

This test validates the fix where InvoiceCreate schema accepts 'villa_ids' from the frontend
and correctly saves the relationships to the invoice_villas junction table.
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.payment import Invoice, InvoiceItem, InvoiceVilla
from app.schemas.payment import InvoiceCreate, InvoiceItemCreate


# ============================================================================
# Test Fixtures
# ============================================================================

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
def test_villas(db: Session) -> list:
    """Create multiple test villas for invoice"""
    villas = []
    
    villa_1 = Villa(
        name="Villa Paradise 1",
        description="First test villa",
        base_price=Decimal("1000000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True
    )
    db.add(villa_1)
    
    villa_2 = Villa(
        name="Villa Paradise 2",
        description="Second test villa",
        base_price=Decimal("1500000.00"),
        capacity="6 guests",
        room_type="Premium",
        is_active=True
    )
    db.add(villa_2)
    
    villa_3 = Villa(
        name="Villa Paradise 3",
        description="Third test villa",
        base_price=Decimal("2000000.00"),
        capacity="8 guests",
        room_type="Luxury",
        is_active=True
    )
    db.add(villa_3)
    
    villa_4 = Villa(
        name="Villa Paradise 4",
        description="Fourth test villa",
        base_price=Decimal("2500000.00"),
        capacity="10 guests",
        room_type="Presidential",
        is_active=True
    )
    db.add(villa_4)
    
    db.commit()
    
    db.refresh(villa_1)
    db.refresh(villa_2)
    db.refresh(villa_3)
    db.refresh(villa_4)
    
    villas = [villa_1, villa_2, villa_3, villa_4]
    return villas


# ============================================================================
# Unit Tests - Direct Database Validation
# ============================================================================

class TestInvoiceVillaIdsSave:
    """Test that villa_ids correctly save to invoice_villas table"""
    
    def test_invoice_creation_with_villa_ids_field(
        self, 
        db: Session, 
        test_user, 
        test_customer, 
        test_package, 
        test_villas
    ):
        """
        Test creating invoice with 'villa_ids' field name (as frontend sends it).
        Validates the validation_alias='villa_ids' fix in InvoiceCreate schema.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Use villa IDs 3 and 4 as per requirements
        villa_id_3 = test_villas[2].id  # Villa Paradise 3
        villa_id_4 = test_villas[3].id  # Villa Paradise 4
        
        # Create invoice data using 'villa_ids' field name (what frontend sends)
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villa_ids=[villa_id_3, villa_id_4],  # Using 'villa_ids' field name
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
        
        # Assert - Verify invoice-villa relationships in database using direct database query
        invoice_villas = db.query(InvoiceVilla).filter(
            InvoiceVilla.invoice_id == invoice.id
        ).all()
        
        # Assert - Exactly 2 villa relationships were created
        assert len(invoice_villas) == 2, f"Expected 2 villa relationships, but got {len(invoice_villas)}"
        
        # Assert - Verify the villa_ids match what was sent
        saved_villa_ids = [iv.villa_id for iv in invoice_villas]
        assert villa_id_3 in saved_villa_ids, f"Villa ID {villa_id_3} not found in saved relationships"
        assert villa_id_4 in saved_villa_ids, f"Villa ID {villa_id_4} not found in saved relationships"
        
        # Assert - Verify each InvoiceVilla record has correct foreign keys
        for invoice_villa in invoice_villas:
            assert invoice_villa.invoice_id == invoice.id
            assert invoice_villa.villa_id in [villa_id_3, villa_id_4]
            
        # Assert - Verify the villa objects are accessible through relationships
        for invoice_villa in invoice_villas:
            assert invoice_villa.villa is not None
            assert invoice_villa.villa.name in ["Villa Paradise 3", "Villa Paradise 4"]
    
    
    def test_invoice_villas_table_structure(
        self, 
        db: Session, 
        test_user, 
        test_customer, 
        test_package, 
        test_villas
    ):
        """
        Test that the invoice_villas junction table has correct structure and relationships.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        villa_id_1 = test_villas[0].id
        villa_id_2 = test_villas[1].id
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villa_ids=[villa_id_1, villa_id_2],
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
        
        # Assert - Query invoice_villas table directly
        invoice_villas = db.query(InvoiceVilla).filter(
            InvoiceVilla.invoice_id == invoice.id
        ).all()
        
        # Assert - Each InvoiceVilla record has required fields
        for iv in invoice_villas:
            assert iv.id is not None, "InvoiceVilla should have an id"
            assert iv.invoice_id is not None, "InvoiceVilla should have invoice_id"
            assert iv.villa_id is not None, "InvoiceVilla should have villa_id"
            
            # Assert - Foreign key relationships work
            assert iv.invoice is not None, "InvoiceVilla.invoice relationship should work"
            assert iv.villa is not None, "InvoiceVilla.villa relationship should work"
            
            # Assert - Relationships point to correct objects
            assert iv.invoice.id == invoice.id
            assert iv.villa.id in [villa_id_1, villa_id_2]
    
    
    def test_invoice_villas_query_count(
        self, 
        db: Session, 
        test_user, 
        test_customer, 
        test_package, 
        test_villas
    ):
        """
        Test that the count of invoice_villas records matches the number of villa_ids sent.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Test with 3 villas
        villa_ids = [test_villas[0].id, test_villas[1].id, test_villas[2].id]
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villa_ids=villa_ids,
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("400000.00"),
                    discount=Decimal("50000.00"),
                    pax=3,
                    line_total=Decimal("350000.00")
                )
            ]
        )
        
        # Act
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Direct count query
        count = db.query(InvoiceVilla).filter(
            InvoiceVilla.invoice_id == invoice.id
        ).count()
        
        assert count == 3, f"Expected 3 villa relationships, but database has {count}"
        
        # Assert - Verify all sent villa_ids are in database
        saved_invoice_villas = db.query(InvoiceVilla).filter(
            InvoiceVilla.invoice_id == invoice.id
        ).all()
        
        saved_villa_ids = {iv.villa_id for iv in saved_invoice_villas}
        expected_villa_ids = set(villa_ids)
        
        assert saved_villa_ids == expected_villa_ids, \
            f"Saved villa_ids {saved_villa_ids} don't match expected {expected_villa_ids}"
    
    
    def test_invoice_with_empty_villa_ids(
        self, 
        db: Session, 
        test_user, 
        test_customer, 
        test_package
    ):
        """
        Test that invoice can be created with empty villa_ids array.
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villa_ids=[],  # Empty villa_ids
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("250000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("250000.00")
                )
            ]
        )
        
        # Act
        from app.services.payment import create_invoice
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice created successfully
        assert invoice is not None
        assert invoice.id is not None
        
        # Assert - No invoice_villas records created
        count = db.query(InvoiceVilla).filter(
            InvoiceVilla.invoice_id == invoice.id
        ).count()
        
        assert count == 0, f"Expected 0 villa relationships, but found {count}"
