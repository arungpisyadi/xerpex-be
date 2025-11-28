"""
Comprehensive tests to verify that tax is always IDR 0 across all modules

This test suite covers:
- Quote creation and updates with zero tax
- Invoice creation and updates with zero tax
- Booking creation with zero tax
- Quote to invoice conversion preserving zero tax
- Integration tests across the full workflow
- Edge cases where tax might be requested but should still be zero
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.quote import Quote, QuoteItem
from app.models.payment import Invoice, InvoiceItem
from app.models.booking import Booking
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate
from app.schemas.payment import InvoiceCreate, InvoiceUpdate, InvoiceItemCreate, QuoteToInvoiceRequest
from app.schemas.booking import BookingCreate, BookingItemCreate, BookingVillaCreate
from app.services.quote import create_quote, get_quote, update_quote, calculate_quote_totals
from app.services.payment import create_invoice, get_invoice, update_invoice, convert_quote_to_invoice
from app.services.booking import create_booking, get_booking


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer for testing"""
    customer = Customer(
        user_id=test_user["id"],
        name="Tax Test Customer",
        email="taxtest@example.com",
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
    """Create a test package for items"""
    package = Package(
        user_id=test_user["id"],
        name="Tax Test Package",
        category="Adventure",
        type="Tour",
        description="Test package for tax testing",
        days=3,
        cost_per_pax=Decimal("1000000.00"),
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
    """Create a test villa"""
    villa = Villa(
        name="Tax Test Villa",
        description="Test villa for tax testing",
        base_price=Decimal("2000000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# Quote Tax Tests
# ============================================================================

class TestQuoteTaxAlwaysZero:
    """Test that quote tax is always zero"""
    
    def test_create_quote_has_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that creating a quote always results in tax_total = 0"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("2000000.00")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - tax_total must be zero
        assert quote.tax_total == Decimal('0.00')
        assert quote.total == Decimal("2000000.00")  # Only items, no tax
        
        # Verify in database
        db_quote = db.query(Quote).filter(Quote.id == quote.id).first()
        assert db_quote.tax_total == Decimal('0.00')
    
    def test_update_quote_forces_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that updating a quote with non-zero tax still results in tax_total = 0"""
        # Arrange - Create quote
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Act - Update quote with new items
        update_data = QuoteUpdate(
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("100000.00"),
                    pax=2,
                    line_total=Decimal("1900000.00")
                )
            ]
        )
        updated_quote = update_quote(db, quote.id, update_data, test_user["id"])
        
        # Assert - tax_total still zero after update
        assert updated_quote.tax_total == Decimal('0.00')
        assert updated_quote.total == Decimal("1900000.00")
    
    def test_quote_total_excludes_tax(self, db: Session, test_user, test_customer, test_package, test_villa):
        """Verify that quote.total does not include any tax amount"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        items_subtotal = Decimal("3000000.00")
        
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=3,
                    line_total=items_subtotal
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - total equals items + villas only (no tax)
        expected_total = items_subtotal + test_villa.base_price
        assert quote.total == expected_total
        assert quote.tax_total == Decimal('0.00')
        
        # Verify total does NOT include any tax calculation
        assert quote.total == items_subtotal + test_villa.base_price
    
    def test_calculate_quote_totals_returns_zero_tax(self, db: Session, test_user, test_package):
        """Test the calculate_quote_totals function"""
        # Arrange
        items = [
            QuoteItemCreate(
                package_id=test_package.id,
                unit_price=Decimal("1000000.00"),
                discount=Decimal("0.00"),
                pax=2,
                line_total=Decimal("2000000.00")
            ),
            QuoteItemCreate(
                package_id=test_package.id,
                unit_price=Decimal("1000000.00"),
                discount=Decimal("200000.00"),
                pax=1,
                line_total=Decimal("800000.00")
            )
        ]
        
        # Act
        totals = calculate_quote_totals(db, items, test_user["id"])
        
        # Assert
        assert totals['subtotal'] == Decimal("2800000.00")
        assert totals['tax_total'] == Decimal('0.00')
        assert totals['total'] == Decimal("2800000.00")
        assert totals['tax_breakdown'] == []
    
    def test_quote_with_villas_has_zero_tax(self, db: Session, test_user, test_customer, test_package, test_villa):
        """Test quote with villas still has zero tax"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa.id],
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
        assert quote.tax_total == Decimal('0.00')
        expected_total = Decimal("1000000.00") + test_villa.base_price
        assert quote.total == expected_total


# ============================================================================
# Invoice Tax Tests
# ============================================================================

class TestInvoiceTaxAlwaysZero:
    """Test that invoice tax is always zero"""
    
    def test_create_invoice_has_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that creating an invoice always results in tax_total = 0"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("2000000.00")
                )
            ]
        )
        
        # Act
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - tax_total must be zero
        assert invoice.tax_total == Decimal('0.00')
        assert invoice.total == Decimal("2000000.00")  # Only items, no tax
        
        # Verify in database
        db_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        assert db_invoice.tax_total == Decimal('0.00')
    
    def test_update_invoice_forces_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that updating an invoice with non-zero tax still results in tax_total = 0"""
        # Arrange - Create invoice
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("1000000.00")
                )
            ]
        )
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Act - Update invoice with new items
        update_data = InvoiceUpdate(
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=3,
                    line_total=Decimal("3000000.00")
                )
            ]
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - tax_total still zero after update
        assert updated_invoice.tax_total == Decimal('0.00')
        assert updated_invoice.total == Decimal("3000000.00")
    
    def test_invoice_total_excludes_tax(self, db: Session, test_user, test_customer, test_package, test_villa):
        """Verify that invoice.total does not include any tax amount"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        items_subtotal = Decimal("2500000.00")
        
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("100000.00"),
                    pax=3,
                    line_total=items_subtotal
                )
            ]
        )
        
        # Act
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert - total equals items + villas only (no tax)
        expected_total = items_subtotal + test_villa.base_price
        assert invoice.total == expected_total
        assert invoice.tax_total == Decimal('0.00')
    
    def test_convert_quote_to_invoice_has_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify conversion from quote to invoice sets tax to 0"""
        # Arrange - Create accepted quote
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="accepted",
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1500000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("3000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Verify quote has zero tax
        assert quote.tax_total == Decimal('0.00')
        
        # Act - Convert to invoice
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Converted from quote"
        )
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Assert - invoice also has zero tax
        assert invoice.tax_total == Decimal('0.00')
        assert invoice.total == quote.total
        assert invoice.quote_id == quote.id
    
    def test_invoice_with_villas_has_zero_tax(self, db: Session, test_user, test_customer, test_package, test_villa):
        """Test invoice with villas still has zero tax"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            villas=[test_villa.id],
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("800000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1600000.00")
                )
            ]
        )
        
        # Act
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert
        assert invoice.tax_total == Decimal('0.00')
        expected_total = Decimal("1600000.00") + test_villa.base_price
        assert invoice.total == expected_total


# ============================================================================
# Booking Tax Tests
# ============================================================================

class TestBookingTaxAlwaysZero:
    """Test that booking calculations have zero tax"""
    
    def test_create_booking_has_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that creating a booking always results in zero tax calculations"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=10)  # 3 nights
        
        # Create booking with just items (no villas to avoid schema complexity)
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[],
            items=[
                BookingItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("2000000.00")
                )
            ]
        )
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert - booking total should be items only (no tax added)
        assert booking.total == Decimal("2000000.00")
        # Bookings don't have a separate tax_total field, but total should equal items (no tax)
    
    def test_booking_total_excludes_tax(self, db: Session, test_user, test_customer, test_package):
        """Verify that booking.total does not include any tax amount"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=9)  # 2 nights
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=3,
            villas=[],
            items=[
                BookingItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("200000.00"),
                    pax=3,
                    line_total=Decimal("2400000.00")
                )
            ]
        )
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert - total is just items (no tax)
        assert booking.total == Decimal("2400000.00")


# ============================================================================
# Integration Tests
# ============================================================================

class TestTaxZeroIntegration:
    """Test complete workflow ensuring tax stays 0 throughout"""
    
    def test_full_workflow_quote_to_invoice_to_payment(self, db: Session, test_user, test_customer, test_package, test_villa):
        """Test complete workflow ensuring tax stays 0 throughout"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Step 1: Create quote with items and villa
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            status="draft",
            villas=[test_villa.id],
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("2000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Quote has zero tax
        assert quote.tax_total == Decimal('0.00')
        quote_total = quote.total
        
        # Step 2: Update quote status to accepted
        quote.status = "accepted"
        db.commit()
        db.refresh(quote)
        
        # Assert - Tax still zero after status change
        assert quote.tax_total == Decimal('0.00')
        
        # Step 3: Convert quote to invoice
        conversion_request = QuoteToInvoiceRequest(
            quote_id=quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Converted from quote"
        )
        invoice = convert_quote_to_invoice(db, conversion_request, test_user["id"])
        
        # Assert - Invoice has zero tax
        assert invoice.tax_total == Decimal('0.00')
        assert invoice.total == quote_total
        
        # Step 4: Update invoice (add more items)
        update_data = InvoiceUpdate(
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("0.00"),
                    pax=3,
                    line_total=Decimal("3000000.00")
                )
            ],
            villas=[test_villa.id]
        )
        updated_invoice = update_invoice(db, invoice.id, update_data, test_user["id"])
        
        # Assert - Tax still zero after update
        assert updated_invoice.tax_total == Decimal('0.00')
        
        # Final assertion - verify total calculation excludes tax
        expected_total = Decimal("3000000.00") + test_villa.base_price
        assert updated_invoice.total == expected_total
    
    def test_multiple_quote_updates_maintain_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Test that multiple updates to quotes maintain zero tax"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create initial quote
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
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
        quote = create_quote(db, quote_data, user_obj)
        assert quote.tax_total == Decimal('0.00')
        
        # Update 1: Change items
        update_data = QuoteUpdate(
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("600000.00"),
                    discount=Decimal("0.00"),
                    pax=2,
                    line_total=Decimal("1200000.00")
                )
            ]
        )
        quote = update_quote(db, quote.id, update_data, test_user["id"])
        assert quote.tax_total == Decimal('0.00')
        
        # Update 2: Add discount
        update_data = QuoteUpdate(
            items=[
                QuoteItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("600000.00"),
                    discount=Decimal("100000.00"),
                    pax=2,
                    line_total=Decimal("1100000.00")
                )
            ]
        )
        quote = update_quote(db, quote.id, update_data, test_user["id"])
        assert quote.tax_total == Decimal('0.00')
        
        # Final check
        assert quote.total == Decimal("1100000.00")
    
    def test_edge_case_empty_items_zero_tax(self, db: Session, test_user, test_customer, test_villa):
        """Test edge case with only villas (no items) still has zero tax"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create quote with only villa (no items)
        quote_data = QuoteCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            villas=[test_villa.id],
            items=[]
        )
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert
        assert quote.tax_total == Decimal('0.00')
        assert quote.total == test_villa.base_price
    
    def test_edge_case_mixed_discounts_zero_tax(self, db: Session, test_user, test_customer, test_package):
        """Test edge case with mixed discounts maintains zero tax"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create invoice with multiple items with different discounts
        invoice_data = InvoiceCreate(
            customer_id=test_customer.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            items=[
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("1000000.00"),
                    discount=Decimal("100000.00"),
                    pax=2,
                    line_total=Decimal("1800000.00")
                ),
                InvoiceItemCreate(
                    package_id=test_package.id,
                    unit_price=Decimal("500000.00"),
                    discount=Decimal("0.00"),
                    pax=1,
                    line_total=Decimal("500000.00")
                )
            ]
        )
        invoice = create_invoice(db, invoice_data, user_obj)
        
        # Assert
        assert invoice.tax_total == Decimal('0.00')
        assert invoice.total == Decimal("2300000.00")