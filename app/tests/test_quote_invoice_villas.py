"""
Comprehensive tests for quote and invoice villa refactoring

This test suite covers:
- Quote villa management (create, update, delete)
- Invoice villa management (create, update, delete)
- Villa junction table relationships
- Cascade delete operations
- Villa validation and error handling
- Total calculation with villas
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.quote import Quote, QuoteItem, QuoteVilla
from app.models.payment import Invoice, InvoiceItem, InvoiceVilla
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate
from app.schemas.payment import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate
from app.services.quote import create_quote, get_quote, update_quote, delete_quote
from app.services.payment import create_invoice, get_invoice, update_invoice, delete_invoice


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer for quotes and invoices"""
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
    """Create a test package for quote/invoice items"""
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
def test_villa_1(db: Session, test_user) -> Villa:
    """Create first test villa"""
    villa = Villa(
        name="Test Villa 1",
        description="First test villa",
        base_price=Decimal("1000000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def test_villa_2(db: Session, test_user) -> Villa:
    """Create second test villa"""
    villa = Villa(
        name="Test Villa 2",
        description="Second test villa",
        base_price=Decimal("1500000.00"),
        capacity="6 guests",
        room_type="Premium",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def test_villa_3(db: Session, test_user) -> Villa:
    """Create third test villa"""
    villa = Villa(
        name="Test Villa 3",
        description="Third test villa",
        base_price=Decimal("2000000.00"),
        capacity="8 guests",
        room_type="Luxury",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# Quote Tests
# ============================================================================

class TestQuoteVillas:
    """Test quote villa operations"""
    
    def test_create_quote_with_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test creating a quote with 2 villa IDs"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id, test_villa_2.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Quote created successfully
        assert quote.id is not None
        assert quote.quote_number is not None
        
        # Assert - 2 QuoteVilla junction records created
        assert len(quote.villas) == 2
        villa_ids = [qv.villa_id for qv in quote.villas]
        assert test_villa_1.id in villa_ids
        assert test_villa_2.id in villa_ids
        
        # Assert - Villa relationships are loaded
        for quote_villa in quote.villas:
            assert quote_villa.villa is not None
            assert quote_villa.villa.name in ["Test Villa 1", "Test Villa 2"]
            assert quote_villa.villa.base_price > 0
        
        # Assert - Total includes villa costs
        expected_total = Decimal("1000000.00") + test_villa_1.base_price + test_villa_2.base_price
        assert quote.total == expected_total
    
    def test_create_quote_without_villas(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with empty villas array"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[],  # Empty villas array
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Quote created successfully
        assert quote.id is not None
        
        # Assert - No QuoteVilla records created
        assert len(quote.villas) == 0
        
        # Assert - Quote works normally with just items
        assert quote.total == Decimal("1000000.00")
    
    def test_create_quote_with_invalid_villa_id(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with non-existent villa ID"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[99999],  # Non-existent villa ID
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_quote(db, quote_data, user_obj)
        
        # Assert error message mentions villa not found
        error_message = str(exc_info.value).lower()
        assert "villa" in error_message and "not found" in error_message
    
    def test_create_quote_with_duplicate_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1):
        """Test creating a quote with duplicate villa IDs raises ValueError"""
        # Arrange & Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            quote_data = QuoteCreate(
                customer_id=test_customer.id,
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=30),
                villas=[test_villa_1.id, test_villa_1.id],  # Duplicate villa IDs
                items=[
                    QuoteItemCreate(
                        package_id=test_package.id,
                        unit_price=Decimal("500000.00"),
                        discount=Decimal("0.00"),
                        pax=2,
                        line_total=Decimal("1000000.00")
                    )
                ]
            )
        
        # Assert error message mentions villas must be unique
        error_message = str(exc_info.value).lower()
        assert "villas must be unique" in error_message or "unique" in error_message
    
    def test_update_quote_add_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test updating a quote to add villas"""
        # Arrange - Create quote without villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        initial_total = quote.total
        
        # Act - Update to add 2 villas
        update_data = QuoteUpdate(
            villas=[test_villa_1.id, test_villa_2.id]
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - QuoteVilla records created
        assert len(updated_quote.villas) == 2
        
        # Assert - Total recalculated correctly
        expected_total = initial_total + test_villa_1.base_price + test_villa_2.base_price
        assert updated_quote.total == expected_total
    
    def test_update_quote_remove_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test updating a quote to remove villas"""
        # Arrange - Create quote with 2 villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id, test_villa_2.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Act - Update to remove villas (empty array)
        update_data = QuoteUpdate(
            villas=[]
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - QuoteVilla records deleted
        assert len(updated_quote.villas) == 0
        
        # Assert - Total recalculated without villas
        assert updated_quote.total == Decimal("1000000.00")  # Only items
    
    def test_update_quote_replace_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2, test_villa_3):
        """Test updating a quote to replace villas"""
        # Arrange - Create quote with villa IDs [1, 2]
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id, test_villa_2.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Act - Update with villa IDs [2, 3] (villa 1 removed, villa 3 added)
        update_data = QuoteUpdate(
            villas=[test_villa_2.id, test_villa_3.id]
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - Villa 1 removed, villa 3 added
        villa_ids = [qv.villa_id for qv in updated_quote.villas]
        assert test_villa_1.id not in villa_ids
        assert test_villa_2.id in villa_ids
        assert test_villa_3.id in villa_ids
        
        # Assert - Total adjusted correctly
        expected_total = Decimal("1000000.00") + test_villa_2.base_price + test_villa_3.base_price
        assert updated_quote.total == expected_total


# ============================================================================
# Invoice Tests
# ============================================================================

class TestInvoiceVillas:
    """Test invoice villa operations"""
    
    def test_create_invoice_with_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test creating an invoice with 2 villa IDs"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id, test_villa_2.id],
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
        
        # Act
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice created successfully
        assert invoice.id is not None
        assert invoice.invoice_number is not None
        
        # Assert - 2 InvoiceVilla junction records created
        assert len(invoice.villas) == 2
        villa_ids = [iv.villa_id for iv in invoice.villas]
        assert test_villa_1.id in villa_ids
        assert test_villa_2.id in villa_ids
        
        # Assert - Villa relationships are loaded
        for invoice_villa in invoice.villas:
            assert invoice_villa.villa is not None
            assert invoice_villa.villa.name in ["Test Villa 1", "Test Villa 2"]
            assert invoice_villa.villa.base_price > 0
        
        # Assert - Total includes villa costs (items + villas + tax)
        expected_subtotal = Decimal("1000000.00") + test_villa_1.base_price + test_villa_2.base_price
        assert invoice.total >= expected_subtotal  # May include tax
    
    def test_create_invoice_without_villas(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice with empty villas array"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[],  # Empty villas array
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
        
        # Act
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - Invoice created successfully
        assert invoice.id is not None
        
        # Assert - No InvoiceVilla records created
        assert len(invoice.villas) == 0
    
    def test_create_invoice_with_invalid_villa_id(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice with non-existent villa ID"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[99999],  # Non-existent villa ID
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
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_invoice(db, invoice_data, user_obj)
        
        # Assert error message mentions villa not found
        error_message = str(exc_info.value).lower()
        assert "villa" in error_message and "not found" in error_message
    
    def test_update_invoice_villas(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2, test_villa_3):
        """Test updating invoice villas"""
        # Arrange - Create invoice with villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id],
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
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Act - Update villas
        update_data = InvoiceUpdate(
            villas=[test_villa_2.id, test_villa_3.id]
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - InvoiceVilla records updated correctly
        villa_ids = [iv.villa_id for iv in updated_invoice.villas]
        assert test_villa_1.id not in villa_ids
        assert test_villa_2.id in villa_ids
        assert test_villa_3.id in villa_ids
        
        # Assert - Total recalculated
        expected_subtotal = Decimal("1000000.00") + test_villa_2.base_price + test_villa_3.base_price
        assert updated_invoice.total >= expected_subtotal


# ============================================================================
# Junction Table Tests
# ============================================================================

class TestJunctionTables:
    """Test quote and invoice villa junction table operations"""
    
    def test_quote_villa_cascade_delete(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test that QuoteVilla records are cascade deleted when quote is deleted"""
        # Arrange - Create quote with villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="draft",
            villas=[test_villa_1.id, test_villa_2.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        quote_id = quote.id
        
        # Verify QuoteVilla records exist
        quote_villa_count = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).count()
        assert quote_villa_count == 2
        
        # Act - Delete quote
        delete_quote(db, quote_id, test_user["id"])
        
        # Assert - QuoteVilla records also deleted (cascade)
        quote_villa_count_after = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).count()
        assert quote_villa_count_after == 0
    
    def test_invoice_villa_cascade_delete(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test that InvoiceVilla records are cascade deleted when invoice is deleted"""
        # Arrange - Create invoice with villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            villas=[test_villa_1.id, test_villa_2.id],
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
        invoice = create_invoice(db, invoice_data, user_obj)
        invoice_id = invoice.id
        
        # Verify InvoiceVilla records exist
        invoice_villa_count = db.query(InvoiceVilla).filter(InvoiceVilla.invoice_id == invoice_id).count()
        assert invoice_villa_count == 2
        
        # Act - Delete invoice
        delete_invoice(db, invoice_id, test_user["id"])
        
        # Assert - InvoiceVilla records also deleted (cascade)
        invoice_villa_count_after = db.query(InvoiceVilla).filter(InvoiceVilla.invoice_id == invoice_id).count()
        assert invoice_villa_count_after == 0
    
    def test_villa_relationships_loaded(self, db: Session, test_user, test_customer, test_package, test_villa_1, test_villa_2):
        """Test that villa relationships are properly loaded with details"""
        # Arrange - Create quote with villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa_1.id, test_villa_2.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Act - Fetch quote
        fetched_quote = get_quote(db, quote.id, user_obj)
        
        # Assert - Villas list populated with Villa objects
        assert len(fetched_quote.villas) == 2
        
        # Assert - Villa details accessible (name, base_price, etc.)
        for quote_villa in fetched_quote.villas:
            villa = quote_villa.villa
            assert villa is not None
            assert villa.name in ["Test Villa 1", "Test Villa 2"]
            assert villa.base_price in [Decimal("1000000.00"), Decimal("1500000.00")]
            assert villa.capacity in ["4 guests", "6 guests"]
            assert villa.room_type in ["Deluxe", "Premium"]
            assert villa.is_active is True