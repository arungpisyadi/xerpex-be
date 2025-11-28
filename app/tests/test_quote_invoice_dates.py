"""
Comprehensive tests for check_in and check_out date functionality in quotes and invoices

This test suite covers:
- Creating quotes with and without check_in/check_out dates
- Updating quotes to add/modify check_in/check_out dates
- Creating invoices with and without check_in/check_out dates
- Updating invoices to add/modify check_in/check_out dates
- Quote-to-invoice conversion with date preservation
- Date validation and edge cases
- Date serialization/deserialization
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.quote import Quote, QuoteItem
from app.models.payment import Invoice, InvoiceItem
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate, QuoteConversionRequest
from app.schemas.payment import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, QuoteToInvoiceRequest
from app.services.quote import create_quote, get_quote, update_quote
from app.services.payment import create_invoice, get_invoice, update_invoice, convert_quote_to_invoice


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer for quotes and invoices"""
    customer = Customer(
        user_id=test_user["id"],
        name="Date Test Customer",
        email="datetest@example.com",
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
        name="Test Package for Dates",
        category="Adventure",
        type="Tour",
        description="Test package for date testing",
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


# ============================================================================
# Quote Tests - check_in and check_out dates
# ============================================================================

class TestQuoteDates:
    """Test quote operations with check_in and check_out dates"""
    
    def test_create_quote_with_dates(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with check_in and check_out dates"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        check_out_date = date.today() + timedelta(days=10)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            check_out=check_out_date,
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
        assert quote.check_in == check_in_date
        assert quote.check_out == check_out_date
        
        # Verify dates are properly stored and retrieved
        fetched_quote = get_quote(db, quote.id, user_obj)
        assert fetched_quote.check_in == check_in_date
        assert fetched_quote.check_out == check_out_date
    
    def test_create_quote_without_dates(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote without check_in and check_out dates (should still work)"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            # No check_in or check_out specified
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
        
        # Assert - Quote created successfully with null dates
        assert quote.id is not None
        assert quote.check_in is None
        assert quote.check_out is None
        
        # Verify quote works normally without dates
        assert quote.total == Decimal("1000000.00")
    
    def test_create_quote_with_only_check_in(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with only check_in date"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            # No check_out
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
        
        # Assert
        assert quote.id is not None
        assert quote.check_in == check_in_date
        assert quote.check_out is None
    
    def test_create_quote_with_only_check_out(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with only check_out date"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_out_date = date.today() + timedelta(days=10)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            # No check_in
            check_out=check_out_date,
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
        
        # Assert
        assert quote.id is not None
        assert quote.check_in is None
        assert quote.check_out == check_out_date
    
    def test_update_quote_add_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating a quote to add check_in and check_out dates"""
        # Arrange - Create quote without dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
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
        
        # Verify no dates initially
        assert quote.check_in is None
        assert quote.check_out is None
        
        # Act - Update to add dates
        check_in_date = date.today() + timedelta(days=14)
        check_out_date = date.today() + timedelta(days=17)
        
        update_data = QuoteUpdate(
            check_in=check_in_date,
            check_out=check_out_date
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - Dates added successfully
        assert updated_quote.check_in == check_in_date
        assert updated_quote.check_out == check_out_date
    
    def test_update_quote_modify_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating a quote to modify existing dates"""
        # Arrange - Create quote with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        original_check_in = date.today() + timedelta(days=7)
        original_check_out = date.today() + timedelta(days=10)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=original_check_in,
            check_out=original_check_out,
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
        
        # Act - Update to new dates
        new_check_in = date.today() + timedelta(days=21)
        new_check_out = date.today() + timedelta(days=24)
        
        update_data = QuoteUpdate(
            check_in=new_check_in,
            check_out=new_check_out
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - Dates updated successfully
        assert updated_quote.check_in == new_check_in
        assert updated_quote.check_out == new_check_out
        assert updated_quote.check_in != original_check_in
        assert updated_quote.check_out != original_check_out
    
    def test_update_quote_remove_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating a quote to remove dates (set to None)"""
        # Arrange - Create quote with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
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
        
        # Verify dates exist
        assert quote.check_in is not None
        assert quote.check_out is not None
        
        # Act - Update to remove dates
        update_data = QuoteUpdate(
            check_in=None,
            check_out=None
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - Dates removed successfully
        assert updated_quote.check_in is None
        assert updated_quote.check_out is None


# ============================================================================
# Invoice Tests - check_in and check_out dates
# ============================================================================

class TestInvoiceDates:
    """Test invoice operations with check_in and check_out dates"""
    
    def test_create_invoice_with_dates(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice with check_in and check_out dates"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        check_out_date = date.today() + timedelta(days=10)
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            check_out=check_out_date,
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
        assert invoice.check_in == check_in_date
        assert invoice.check_out == check_out_date
        
        # Verify dates are properly stored and retrieved
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        assert fetched_invoice.check_in == check_in_date
        assert fetched_invoice.check_out == check_out_date
    
    def test_create_invoice_without_dates(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice without check_in and check_out dates (should still work)"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            # No check_in or check_out specified
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
        
        # Assert - Invoice created successfully with null dates
        assert invoice.id is not None
        assert invoice.check_in is None
        assert invoice.check_out is None
        
        # Verify invoice works normally without dates
        assert invoice.total > Decimal("0.00")
    
    def test_create_invoice_with_only_check_in(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice with only check_in date"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            # No check_out
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
        
        # Assert
        assert invoice.id is not None
        assert invoice.check_in == check_in_date
        assert invoice.check_out is None
    
    def test_create_invoice_with_only_check_out(self, db: Session, test_user, test_customer, test_package):
        """Test creating an invoice with only check_out date"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_out_date = date.today() + timedelta(days=10)
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            # No check_in
            check_out=check_out_date,
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
        
        # Assert
        assert invoice.id is not None
        assert invoice.check_in is None
        assert invoice.check_out == check_out_date
    
    def test_update_invoice_add_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating an invoice to add check_in and check_out dates"""
        # Arrange - Create invoice without dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
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
        
        # Verify no dates initially
        assert invoice.check_in is None
        assert invoice.check_out is None
        
        # Act - Update to add dates
        check_in_date = date.today() + timedelta(days=14)
        check_out_date = date.today() + timedelta(days=17)
        
        update_data = InvoiceUpdate(
            check_in=check_in_date,
            check_out=check_out_date
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - Dates added successfully
        assert updated_invoice.check_in == check_in_date
        assert updated_invoice.check_out == check_out_date
    
    def test_update_invoice_modify_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating an invoice to modify existing dates"""
        # Arrange - Create invoice with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        original_check_in = date.today() + timedelta(days=7)
        original_check_out = date.today() + timedelta(days=10)
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            check_in=original_check_in,
            check_out=original_check_out,
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
        
        # Act - Update to new dates
        new_check_in = date.today() + timedelta(days=21)
        new_check_out = date.today() + timedelta(days=24)
        
        update_data = InvoiceUpdate(
            check_in=new_check_in,
            check_out=new_check_out
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - Dates updated successfully
        assert updated_invoice.check_in == new_check_in
        assert updated_invoice.check_out == new_check_out
        assert updated_invoice.check_in != original_check_in
        assert updated_invoice.check_out != original_check_out
    
    def test_update_invoice_remove_dates(self, db: Session, test_user, test_customer, test_package):
        """Test updating an invoice to remove dates (set to None)"""
        # Arrange - Create invoice with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
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
        
        # Verify dates exist
        assert invoice.check_in is not None
        assert invoice.check_out is not None
        
        # Act - Update to remove dates
        update_data = InvoiceUpdate(
            check_in=None,
            check_out=None
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - Dates removed successfully
        assert updated_invoice.check_in is None
        assert updated_invoice.check_out is None


# ============================================================================
# Quote to Invoice Conversion Tests
# ============================================================================

class TestQuoteToInvoiceConversion:
    """Test that check_in and check_out dates are properly copied during conversion"""
    
    def test_convert_quote_with_dates_to_invoice(self, db: Session, test_user, test_customer, test_package):
        """Test converting a quote with dates to invoice preserves the dates"""
        # Arrange - Create accepted quote with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        check_out_date = date.today() + timedelta(days=10)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            check_out=check_out_date,
            status="accepted",  # Must be accepted for conversion
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
        
        # Act - Convert quote to invoice
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Converted from quote"
        )
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Assert - Dates copied correctly
        assert invoice.id is not None
        assert invoice.quote_id == quote.id
        assert invoice.check_in == check_in_date
        assert invoice.check_out == check_out_date
        assert invoice.check_in == quote.check_in
        assert invoice.check_out == quote.check_out
    
    def test_convert_quote_without_dates_to_invoice(self, db: Session, test_user, test_customer, test_package):
        """Test converting a quote without dates to invoice preserves null values"""
        # Arrange - Create accepted quote without dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            # No check_in or check_out
            status="accepted",
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
        
        # Act - Convert quote to invoice
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Converted from quote without dates"
        )
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Assert - Null dates preserved
        assert invoice.id is not None
        assert invoice.quote_id == quote.id
        assert invoice.check_in is None
        assert invoice.check_out is None
        assert invoice.check_in == quote.check_in
        assert invoice.check_out == quote.check_out
    
    def test_convert_quote_with_only_check_in_to_invoice(self, db: Session, test_user, test_customer, test_package):
        """Test converting a quote with only check_in date"""
        # Arrange - Create accepted quote with only check_in
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            # No check_out
            status="accepted",
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
        
        # Act - Convert quote to invoice
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Assert - Only check_in copied
        assert invoice.check_in == check_in_date
        assert invoice.check_out is None


# ============================================================================
# Edge Cases and Date Validation Tests
# ============================================================================

class TestDateEdgeCases:
    """Test edge cases and date validation scenarios"""
    
    def test_quote_with_past_check_in_date(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with check_in date in the past is allowed"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        past_check_in = date.today() - timedelta(days=7)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=past_check_in,
            check_out=date.today(),
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
        
        # Act - Should not raise error (business logic may not enforce future dates)
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert
        assert quote.check_in == past_check_in
    
    def test_quote_with_same_check_in_and_check_out(self, db: Session, test_user, test_customer, test_package):
        """Test creating a quote with same check_in and check_out dates"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        same_date = date.today() + timedelta(days=7)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=same_date,
            check_out=same_date,
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("500000.00")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Same dates are allowed
        assert quote.check_in == same_date
        assert quote.check_out == same_date
    
    def test_invoice_date_serialization(self, db: Session, test_user, test_customer, test_package):
        """Test that dates are properly serialized/deserialized"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date(2024, 12, 25)  # Specific date for testing
        check_out_date = date(2024, 12, 28)
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            check_out=check_out_date,
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
        fetched_invoice = get_invoice(db, invoice.id, user_obj)
        
        # Assert - Dates are date objects, not datetime or strings
        assert isinstance(fetched_invoice.check_in, date)
        assert isinstance(fetched_invoice.check_out, date)
        assert fetched_invoice.check_in == check_in_date
        assert fetched_invoice.check_out == check_out_date
    
    def test_multiple_updates_preserve_dates(self, db: Session, test_user, test_customer, test_package):
        """Test that multiple updates don't accidentally clear dates"""
        # Arrange - Create quote with dates
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in_date = date.today() + timedelta(days=7)
        check_out_date = date.today() + timedelta(days=10)
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=check_in_date,
            check_out=check_out_date,
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
        
        # Act - Update notes (not dates)
        update_data = QuoteUpdate(notes="Updated notes")
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - Dates are preserved
        assert updated_quote.check_in == check_in_date
        assert updated_quote.check_out == check_out_date
        
        # Act again - Update status (not dates)
        status_update = QuoteUpdate(status="sent")
        updated_quote = update_quote(db, quote.id, status_update, test_user["id"])
        
        # Assert - Dates still preserved
        assert updated_quote.check_in == check_in_date
        assert updated_quote.check_out == check_out_date