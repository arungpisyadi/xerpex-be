"""
Test cases for pax field functionality in quotes and invoices modules
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.package import Package
from app.models.quote import Quote, QuoteItem
from app.models.payment import Invoice, InvoiceItem
from app.models.user import User
from app.utils.security import get_password_hash


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_customer(db: Session, user_id: int, name: str = "Test Customer") -> Customer:
    """
    Create a test customer for use in quotes and invoices
    
    Args:
        db: Database session
        user_id: User ID who owns the customer
        name: Customer name
        
    Returns:
        Customer: Created customer object
    """
    customer = Customer(
        user_id=user_id,
        name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        phone_number="+6281234567890",
        address="Test Address 123",
        billing_address="Test Billing Address 123",
        status=1,
        created_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_test_package(db: Session, user_id: int, name: str = "Test Package") -> Package:
    """
    Create a test package for use in quotes and invoices
    
    Args:
        db: Database session
        user_id: User ID who owns the package
        name: Package name
        
    Returns:
        Package: Created package object
    """
    package = Package(
        user_id=user_id,
        name=name,
        description="Test package description",
        cost_per_pax=Decimal("1000000.00"),
        category="accommodation",
        type="standard",
        days=1,
        min_pax=1,
        created_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


def create_test_quote_with_pax(
    db: Session,
    user_id: int,
    customer_id: int,
    package_id: int,
    pax: int = 1
) -> Quote:
    """
    Create a test quote with a specified pax value
    
    Args:
        db: Database session
        user_id: User ID who owns the quote
        customer_id: Customer ID
        package_id: Package ID
        pax: Number of pax (default 1)
        
    Returns:
        Quote: Created quote object with items
    """
    quote = Quote(
        user_id=user_id,
        customer_id=customer_id,
        quote_number=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}",
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal("1000000.00"),
        tax_total=Decimal("0.00"),
        created_at=datetime.utcnow()
    )
    db.add(quote)
    db.flush()
    
    # Add quote item with pax
    quote_item = QuoteItem(
        quote_id=quote.id,
        package_id=package_id,
        pax=pax,
        unit_price=Decimal("1000000.00"),
        discount=Decimal("0.00"),
        line_total=Decimal("1000000.00"),
        created_at=datetime.utcnow()
    )
    db.add(quote_item)
    db.commit()
    db.refresh(quote)
    return quote


def create_test_invoice_with_pax(
    db: Session,
    user_id: int,
    customer_id: int,
    package_id: int,
    pax: int = 1
) -> Invoice:
    """
    Create a test invoice with a specified pax value
    
    Args:
        db: Database session
        user_id: User ID who owns the invoice
        customer_id: Customer ID
        package_id: Package ID
        pax: Number of pax (default 1)
        
    Returns:
        Invoice: Created invoice object with items
    """
    invoice = Invoice(
        user_id=user_id,
        customer_id=customer_id,
        invoice_number=f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal("1000000.00"),
        tax_total=Decimal("0.00"),
        created_at=datetime.utcnow()
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item with pax
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package_id,
        pax=pax,
        unit_price=Decimal("1000000.00"),
        discount=Decimal("0.00"),
        line_total=Decimal("1000000.00"),
        created_at=datetime.utcnow()
    )
    db.add(invoice_item)
    db.commit()
    db.refresh(invoice)
    return invoice


# ============================================================================
# Test Cases
# ============================================================================

class TestQuotePaxField:
    """Test cases for pax field in quotes"""
    
    def test_create_quote_with_custom_pax(self, db: Session, test_user):
        """
        Test creating a quote with custom pax values
        
        Verifies that:
        - Quote items can be created with custom pax values
        - Pax values are saved correctly in the database
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote with pax=5
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=5
        )
        
        # Verify quote was created
        assert quote.id is not None
        assert len(quote.items) == 1
        
        # Verify pax value
        quote_item = quote.items[0]
        assert quote_item.pax == 5
        assert quote_item.package_id == package.id
    
    def test_create_quote_with_default_pax(self, db: Session, test_user):
        """
        Test creating a quote without specifying pax (should default to 1)
        
        Verifies that:
        - When pax is not specified, it defaults to 1
        - Default value works correctly
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote without explicit pax (uses default)
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id
            # pax not specified, should default to 1
        )
        
        # Verify default pax value
        assert len(quote.items) == 1
        quote_item = quote.items[0]
        assert quote_item.pax == 1
    
    def test_update_quote_pax_value(self, db: Session, test_user):
        """
        Test updating pax value in existing quote items
        
        Verifies that:
        - Pax values can be updated
        - Updates are persisted correctly
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote with pax=2
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=2
        )
        
        # Update pax to 4
        quote_item = quote.items[0]
        quote_item.pax = 4
        db.commit()
        db.refresh(quote_item)
        
        # Verify update
        assert quote_item.pax == 4
    
    def test_quote_with_multiple_items_different_pax(self, db: Session, test_user):
        """
        Test creating a quote with multiple items having different pax values
        
        Verifies that:
        - Multiple items can have different pax values
        - Each item maintains its own pax value independently
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package1 = create_test_package(db, test_user["id"], "Package 1")
        package2 = create_test_package(db, test_user["id"], "Package 2")
        
        # Create quote
        quote = Quote(
            user_id=test_user["id"],
            customer_id=customer.id,
            quote_number=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("2000000.00"),
            tax_total=Decimal("0.00"),
            created_at=datetime.utcnow()
        )
        db.add(quote)
        db.flush()
        
        # Add first item with pax=3
        item1 = QuoteItem(
            quote_id=quote.id,
            package_id=package1.id,
            pax=3,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item1)
        
        # Add second item with pax=5
        item2 = QuoteItem(
            quote_id=quote.id,
            package_id=package2.id,
            pax=5,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item2)
        
        db.commit()
        db.refresh(quote)
        
        # Verify both items have correct pax values
        assert len(quote.items) == 2
        assert quote.items[0].pax == 3
        assert quote.items[1].pax == 5


class TestInvoicePaxField:
    """Test cases for pax field in invoices"""
    
    def test_create_invoice_with_custom_pax(self, db: Session, test_user):
        """
        Test creating an invoice with custom pax values
        
        Verifies that:
        - Invoice items can be created with custom pax values
        - Pax values are saved correctly in the database
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create invoice with pax=4
        invoice = create_test_invoice_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=4
        )
        
        # Verify invoice was created
        assert invoice.id is not None
        assert len(invoice.items) == 1
        
        # Verify pax value
        invoice_item = invoice.items[0]
        assert invoice_item.pax == 4
        assert invoice_item.package_id == package.id
    
    def test_create_invoice_with_default_pax(self, db: Session, test_user):
        """
        Test creating an invoice without specifying pax (should default to 1)
        
        Verifies that:
        - When pax is not specified, it defaults to 1
        - Default value works correctly for invoices
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create invoice without explicit pax (uses default)
        invoice = create_test_invoice_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id
            # pax not specified, should default to 1
        )
        
        # Verify default pax value
        assert len(invoice.items) == 1
        invoice_item = invoice.items[0]
        assert invoice_item.pax == 1
    
    def test_update_invoice_pax_value(self, db: Session, test_user):
        """
        Test updating pax value in existing invoice items
        
        Verifies that:
        - Pax values can be updated on invoices
        - Updates are persisted correctly
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create invoice with pax=3
        invoice = create_test_invoice_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=3
        )
        
        # Update pax to 6
        invoice_item = invoice.items[0]
        invoice_item.pax = 6
        db.commit()
        db.refresh(invoice_item)
        
        # Verify update
        assert invoice_item.pax == 6
    
    def test_invoice_with_multiple_items_different_pax(self, db: Session, test_user):
        """
        Test creating an invoice with multiple items having different pax values
        
        Verifies that:
        - Multiple invoice items can have different pax values
        - Each item maintains its own pax value independently
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package1 = create_test_package(db, test_user["id"], "Package 1")
        package2 = create_test_package(db, test_user["id"], "Package 2")
        
        # Create invoice
        invoice = Invoice(
            user_id=test_user["id"],
            customer_id=customer.id,
            invoice_number=f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("2000000.00"),
            tax_total=Decimal("0.00"),
            created_at=datetime.utcnow()
        )
        db.add(invoice)
        db.flush()
        
        # Add first item with pax=2
        item1 = InvoiceItem(
            invoice_id=invoice.id,
            package_id=package1.id,
            pax=2,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item1)
        
        # Add second item with pax=8
        item2 = InvoiceItem(
            invoice_id=invoice.id,
            package_id=package2.id,
            pax=8,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item2)
        
        db.commit()
        db.refresh(invoice)
        
        # Verify both items have correct pax values
        assert len(invoice.items) == 2
        assert invoice.items[0].pax == 2
        assert invoice.items[1].pax == 8


class TestQuoteToInvoiceConversion:
    """Test cases for quote-to-invoice conversion with pax transfer"""
    
    def test_quote_to_invoice_transfers_pax(self, db: Session, test_user):
        """
        Test that pax values are correctly transferred when converting quote to invoice
        
        Verifies that:
        - Pax values from quote items are transferred to invoice items
        - Conversion logic preserves pax information
        - Multiple items with different pax values are all transferred correctly
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package1 = create_test_package(db, test_user["id"], "Package A")
        package2 = create_test_package(db, test_user["id"], "Package B")
        
        # Create quote with multiple items having different pax values
        quote = Quote(
            user_id=test_user["id"],
            customer_id=customer.id,
            quote_number=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="accepted",  # Must be accepted for conversion
            total=Decimal("2000000.00"),
            tax_total=Decimal("100000.00"),
            created_at=datetime.utcnow()
        )
        db.add(quote)
        db.flush()
        
        # Add quote items with specific pax values
        item1 = QuoteItem(
            quote_id=quote.id,
            package_id=package1.id,
            pax=3,
            unit_price=Decimal("500000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("500000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item1)
        
        item2 = QuoteItem(
            quote_id=quote.id,
            package_id=package2.id,
            pax=7,
            unit_price=Decimal("1500000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1500000.00"),
            created_at=datetime.utcnow()
        )
        db.add(item2)
        
        db.commit()
        db.refresh(quote)
        
        # Convert quote to invoice using the service function
        from app.services.payment import convert_quote_to_invoice
        from app.schemas.payment import QuoteToInvoiceRequest
        
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Converted from quote"
        )
        
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Verify invoice was created
        assert invoice.id is not None
        assert invoice.quote_id == quote.id
        assert len(invoice.items) == 2
        
        # Verify pax values were transferred correctly
        invoice_items_by_package = {item.package_id: item for item in invoice.items}
        
        assert invoice_items_by_package[package1.id].pax == 3
        assert invoice_items_by_package[package2.id].pax == 7
    
    def test_quote_to_invoice_transfers_default_pax(self, db: Session, test_user):
        """
        Test that default pax value (1) is transferred during quote-to-invoice conversion
        
        Verifies that:
        - Items with pax=1 are correctly transferred
        - Default values work correctly in conversion process
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote with default pax=1
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=1
        )
        
        # Update status to accepted for conversion
        quote.status = "accepted"
        db.commit()
        db.refresh(quote)
        
        # Convert quote to invoice
        from app.services.payment import convert_quote_to_invoice
        from app.schemas.payment import QuoteToInvoiceRequest
        
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Verify pax=1 was transferred
        assert len(invoice.items) == 1
        assert invoice.items[0].pax == 1


class TestPaxValidation:
    """Test cases for pax field validation"""
    
    def test_pax_less_than_one_raises_error(self, db: Session, test_user):
        """
        Test that creating item with pax < 1 raises validation error
        
        Verifies that:
        - Pax values less than 1 are rejected
        - Appropriate error is raised
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Attempt to create quote item with pax=0
        quote = Quote(
            user_id=test_user["id"],
            customer_id=customer.id,
            quote_number=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="draft",
            total=Decimal("1000000.00"),
            tax_total=Decimal("0.00"),
            created_at=datetime.utcnow()
        )
        db.add(quote)
        db.flush()
        
        # This should work at DB level (no constraint), but schema validation would catch it
        quote_item = QuoteItem(
            quote_id=quote.id,
            package_id=package.id,
            pax=0,  # Invalid value
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00"),
            created_at=datetime.utcnow()
        )
        db.add(quote_item)
        db.commit()
        
        # At DB level, this works, but schema validation will catch it
        # Test schema validation
        from app.schemas.quote import QuoteItemBase
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            QuoteItemBase(
                package_id=package.id,
                pax=0,
                unit_price=Decimal("1000000.00"),
                discount=Decimal("0.00"),
                line_total=Decimal("1000000.00")
            )
        
        assert "pax must be at least 1" in str(exc_info.value)
    
    def test_pax_negative_raises_error(self, db: Session, test_user):
        """
        Test that creating item with negative pax raises validation error
        
        Verifies that:
        - Negative pax values are rejected
        - Schema validation catches invalid values
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Test schema validation for invoice item
        from app.schemas.payment import InvoiceItemBase
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            InvoiceItemBase(
                package_id=package.id,
                pax=-5,
                unit_price=Decimal("1000000.00"),
                discount=Decimal("0.00"),
                line_total=Decimal("1000000.00")
            )
        
        assert "pax must be at least 1" in str(exc_info.value)
    
    def test_pax_equals_one_is_valid(self, db: Session, test_user):
        """
        Test that pax=1 is accepted as the minimum valid value
        
        Verifies that:
        - pax=1 is valid (minimum acceptable value)
        - No validation errors are raised for pax=1
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote with pax=1 (should be valid)
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=1
        )
        
        # Verify creation was successful
        assert quote.id is not None
        assert quote.items[0].pax == 1
        
        # Also test schema validation
        from app.schemas.quote import QuoteItemBase
        
        item_data = QuoteItemBase(
            package_id=package.id,
            pax=1,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00")
        )
        
        assert item_data.pax == 1
    
    def test_large_pax_values_accepted(self, db: Session, test_user):
        """
        Test that large pax values (e.g., 100+) are accepted
        
        Verifies that:
        - System can handle large pax values
        - No upper limit validation errors occur
        - Large values are stored correctly
        """
        # Setup test data
        customer = create_test_customer(db, test_user["id"])
        package = create_test_package(db, test_user["id"])
        
        # Create quote with large pax value
        large_pax = 150
        quote = create_test_quote_with_pax(
            db,
            user_id=test_user["id"],
            customer_id=customer.id,
            package_id=package.id,
            pax=large_pax
        )
        
        # Verify large value was stored correctly
        assert quote.id is not None
        assert quote.items[0].pax == large_pax
        
        # Also test schema validation with very large value
        from app.schemas.payment import InvoiceItemBase
        
        item_data = InvoiceItemBase(
            package_id=package.id,
            pax=999,
            unit_price=Decimal("1000000.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("1000000.00")
        )
        
        assert item_data.pax == 999