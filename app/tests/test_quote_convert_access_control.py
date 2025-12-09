"""
Comprehensive tests for quote-to-invoice conversion access control

This test suite verifies the fix for role-based access control in the
convert_quote_to_invoice() function. The fix ensures that:
- Admin/finance/sales users can convert quotes created by any user
- Regular sales users can only convert their own quotes

Test Coverage:
1. Admin user access to convert any quote
2. Finance user access to convert any quote
3. Sales user access to convert any quote
4. Regular user can convert their own quotes
5. Regular user cannot convert quotes from other users (404)
6. Edge cases: non-existent quotes, quotes without items/villas
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.quote import Quote, QuoteItem, QuoteVilla
from app.models.payment import Invoice
from app.models.villa import Villa
from app.schemas.payment import QuoteToInvoiceRequest
from app.services.payment import convert_quote_to_invoice
from app.services.quote import create_quote
from app.schemas.quote import QuoteCreate, QuoteItemCreate


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing"""
    user = User(
        username="admin_convert",
        email="admin_convert@example.com",
        full_name="Admin Converter",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='admin'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def finance_user(db: Session) -> User:
    """Create a finance user for testing"""
    user = User(
        username="finance_convert",
        email="finance_convert@example.com",
        full_name="Finance Converter",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='finance'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sales_user(db: Session) -> User:
    """Create a sales user for testing"""
    user = User(
        username="sales_convert",
        email="sales_convert@example.com",
        full_name="Sales Converter",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='sales'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def regular_user(db: Session) -> User:
    """Create a regular user for testing"""
    user = User(
        username="regular_convert",
        email="regular_convert@example.com",
        full_name="Regular Converter",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: Session) -> User:
    """Create another regular user for testing cross-user access"""
    user = User(
        username="other_convert",
        email="other_convert@example.com",
        full_name="Other Converter",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def customer_for_user(db: Session, other_user: User) -> Customer:
    """Create a customer for the other user"""
    customer = Customer(
        user_id=other_user.id,
        name="Test Customer for Quote Conversion",
        email="quote_customer@test.com",
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
def package_for_user(db: Session, other_user: User) -> Package:
    """Create a package for the other user"""
    package = Package(
        user_id=other_user.id,
        name="Test Package for Quote Conversion",
        category="Adventure",
        type="Tour",
        description="Test package for conversion",
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
def villa_for_testing(db: Session) -> Villa:
    """Create a villa for testing"""
    villa = Villa(
        name="Test Villa for Conversion",
        description="Test villa in Bali",
        capacity="4",
        room_type="Deluxe",
        base_price=Decimal("2000000.00"),
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def accepted_quote_by_other_user(
    db: Session,
    other_user: User,
    customer_for_user: Customer,
    package_for_user: Package,
    villa_for_testing: Villa
) -> Quote:
    """Create an accepted quote by other_user with items and villas"""
    quote_data = QuoteCreate(
        customer_id=customer_for_user.id,
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status="draft",
        total=Decimal("52000000.00"),
        items=[
            QuoteItemCreate(
                package_id=package_for_user.id,
                unit_price=Decimal("500000.00"),
                pax=100,
                discount=Decimal("0"),
                line_total=Decimal("50000000.00")
            )
        ],
        villas=[villa_for_testing.id]
    )
    quote = create_quote(db, quote_data, other_user)
    
    # Update status to accepted
    quote.status = "accepted"
    db.commit()
    db.refresh(quote)
    return quote


@pytest.fixture
def accepted_quote_by_regular_user(
    db: Session,
    regular_user: User,
    villa_for_testing: Villa
) -> Quote:
    """Create an accepted quote by regular_user"""
    # Create customer for regular user
    customer = Customer(
        user_id=regular_user.id,
        name="Regular User Customer",
        email="regular_customer@test.com",
        phone_number="6281234567891",
        address="Regular Address",
        billing_address="Regular Billing",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create package for regular user
    package = Package(
        user_id=regular_user.id,
        name="Regular User Package",
        category="Adventure",
        type="Tour",
        description="Test package for regular user",
        days=3,
        cost_per_pax=Decimal("500000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    quote_data = QuoteCreate(
        customer_id=customer.id,
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status="draft",
        total=Decimal("52000000.00"),
        items=[
            QuoteItemCreate(
                package_id=package.id,
                unit_price=Decimal("500000.00"),
                pax=100,
                discount=Decimal("0"),
                line_total=Decimal("50000000.00")
            )
        ],
        villas=[villa_for_testing.id]
    )
    quote = create_quote(db, quote_data, regular_user)
    
    # Update status to accepted
    quote.status = "accepted"
    db.commit()
    db.refresh(quote)
    return quote


# ============================================================================
# Test Classes
# ============================================================================

class TestAdminUserConvertAccess:
    """Test admin user access to convert quotes"""
    
    def test_admin_can_convert_quote_from_other_user(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that admin user can convert quotes created by any user.
        
        Admin users should bypass user isolation and successfully convert
        quotes regardless of who created them.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Admin converted this quote"
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert invoice is not None
        assert invoice.quote_id == accepted_quote_by_other_user.id
        assert invoice.user_id == admin_user.id  # Invoice owned by admin
        assert invoice.customer_id == accepted_quote_by_other_user.customer_id
        assert invoice.total == accepted_quote_by_other_user.total
        assert invoice.notes == "Admin converted this quote"
        assert len(invoice.items) == len(accepted_quote_by_other_user.items)
        assert len(invoice.villas) == len(accepted_quote_by_other_user.villas)
    
    def test_admin_can_convert_multiple_quotes_from_different_users(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote,
        accepted_quote_by_regular_user: Quote
    ):
        """
        Test that admin can convert multiple quotes from different users.
        """
        # Convert first quote
        request1 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice1 = convert_quote_to_invoice(db, request1, admin_user)
        
        # Convert second quote
        request2 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_regular_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice2 = convert_quote_to_invoice(db, request2, admin_user)
        
        # Assert both conversions succeeded
        assert invoice1 is not None
        assert invoice2 is not None
        assert invoice1.quote_id == accepted_quote_by_other_user.id
        assert invoice2.quote_id == accepted_quote_by_regular_user.id


class TestFinanceUserConvertAccess:
    """Test finance user access to convert quotes"""
    
    def test_finance_can_convert_quote_from_other_user(
        self,
        db: Session,
        finance_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that finance user can convert quotes created by any user.
        
        Finance users should bypass user isolation and successfully convert
        quotes regardless of who created them.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Finance converted this quote"
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, finance_user)
        
        # Assert
        assert invoice is not None
        assert invoice.quote_id == accepted_quote_by_other_user.id
        assert invoice.user_id == finance_user.id
        assert invoice.customer_id == accepted_quote_by_other_user.customer_id
        assert invoice.total == accepted_quote_by_other_user.total
        assert len(invoice.items) > 0
        assert len(invoice.villas) > 0


class TestSalesUserConvertAccess:
    """Test sales user access to convert quotes"""
    
    def test_sales_can_convert_quote_from_other_user(
        self,
        db: Session,
        sales_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that sales user can convert quotes created by any user.
        
        Sales users should bypass user isolation and successfully convert
        quotes regardless of who created them.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="Sales converted this quote"
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, sales_user)
        
        # Assert
        assert invoice is not None
        assert invoice.quote_id == accepted_quote_by_other_user.id
        assert invoice.user_id == sales_user.id
        assert invoice.customer_id == accepted_quote_by_other_user.customer_id
        assert invoice.total == accepted_quote_by_other_user.total
        assert len(invoice.items) > 0
        assert len(invoice.villas) > 0


class TestRegularUserConvertAccess:
    """Test regular user access to convert quotes"""
    
    def test_regular_user_can_convert_own_quote(
        self,
        db: Session,
        regular_user: User,
        accepted_quote_by_regular_user: Quote
    ):
        """
        Test that regular user can convert their own quotes successfully.
        
        Regular users should be able to convert quotes they created themselves.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_regular_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            notes="User converted their own quote"
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, regular_user)
        
        # Assert
        assert invoice is not None
        assert invoice.quote_id == accepted_quote_by_regular_user.id
        assert invoice.user_id == regular_user.id
        assert invoice.customer_id == accepted_quote_by_regular_user.customer_id
        assert invoice.total == accepted_quote_by_regular_user.total
        assert len(invoice.items) > 0
        assert len(invoice.villas) > 0
    
    def test_regular_user_cannot_convert_other_users_quote(
        self,
        db: Session,
        regular_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that regular user CANNOT convert quotes created by other users.
        
        Regular users should be restricted by user isolation and get 404
        when trying to convert quotes they don't own.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            convert_quote_to_invoice(db, conversion_request, regular_user)
        
        # Assert - Should return 404 (quote not found due to isolation)
        assert exc_info.value.status_code == 404
        assert "quote not found" in exc_info.value.detail.lower()


class TestEdgeCasesConversion:
    """Test edge cases in quote conversion"""
    
    def test_convert_non_existent_quote_returns_404(
        self,
        db: Session,
        admin_user: User
    ):
        """
        Test that attempting to convert a non-existent quote returns 404.
        """
        # Arrange
        non_existent_quote_id = 999999
        conversion_request = QuoteToInvoiceRequest(
            quote_id=non_existent_quote_id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            convert_quote_to_invoice(db, conversion_request, admin_user)
        
        assert exc_info.value.status_code == 404
        assert "quote not found" in exc_info.value.detail.lower()
    
    def test_convert_draft_quote_fails(
        self,
        db: Session,
        admin_user: User,
        other_user: User,
        customer_for_user: Customer,
        package_for_user: Package
    ):
        """
        Test that only accepted quotes can be converted to invoices.
        """
        # Create a draft quote (not accepted)
        quote_data = QuoteCreate(
            customer_id=customer_for_user.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=13),
            status="draft",
            total=Decimal("50000000.00"),
            items=[
                QuoteItemCreate(
                    package_id=package_for_user.id,
                    unit_price=Decimal("500000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("50000000.00")
                )
            ]
        )
        draft_quote = create_quote(db, quote_data, other_user)
        
        # Try to convert draft quote
        conversion_request = QuoteToInvoiceRequest(
            quote_id=draft_quote.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Should fail with 400 (only accepted quotes can be converted)
        with pytest.raises(HTTPException) as exc_info:
            convert_quote_to_invoice(db, conversion_request, admin_user)
        
        assert exc_info.value.status_code == 400
        assert "accepted" in exc_info.value.detail.lower()
    
    def test_convert_already_converted_quote_fails(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that a quote cannot be converted twice.
        """
        # First conversion
        request1 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice1 = convert_quote_to_invoice(db, request1, admin_user)
        assert invoice1 is not None
        
        # Second conversion attempt should fail
        request2 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            convert_quote_to_invoice(db, request2, admin_user)
        
        assert exc_info.value.status_code == 400
        assert "already been converted" in exc_info.value.detail.lower()
    
    def test_convert_quote_preserves_check_in_out_dates(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that check_in and check_out dates are preserved from quote to invoice.
        """
        # Arrange
        original_check_in = accepted_quote_by_other_user.check_in
        original_check_out = accepted_quote_by_other_user.check_out
        
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert invoice.check_in == original_check_in
        assert invoice.check_out == original_check_out
    
    def test_convert_quote_creates_invoice_with_correct_items(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that all quote items are correctly copied to the invoice.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert len(invoice.items) == len(accepted_quote_by_other_user.items)
        
        # Check each item
        for quote_item, invoice_item in zip(accepted_quote_by_other_user.items, invoice.items):
            assert invoice_item.package_id == quote_item.package_id
            assert invoice_item.unit_price == quote_item.unit_price
            assert invoice_item.discount == quote_item.discount
            assert invoice_item.line_total == quote_item.line_total
            assert invoice_item.pax == quote_item.pax
    
    def test_convert_quote_creates_invoice_with_correct_villas(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that all quote villas are correctly copied to the invoice.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert len(invoice.villas) == len(accepted_quote_by_other_user.villas)
        
        # Check villa associations
        quote_villa_ids = {qv.villa_id for qv in accepted_quote_by_other_user.villas}
        invoice_villa_ids = {iv.villa_id for iv in invoice.villas}
        assert invoice_villa_ids == quote_villa_ids


class TestConversionDataIntegrity:
    """Test data integrity during conversion"""
    
    def test_converted_invoice_has_draft_status(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that newly converted invoices start with 'draft' status.
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert invoice.status == "draft"
    
    def test_converted_invoice_has_unique_invoice_number(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote,
        accepted_quote_by_regular_user: Quote
    ):
        """
        Test that each converted invoice gets a unique invoice number.
        """
        # Convert first quote
        request1 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice1 = convert_quote_to_invoice(db, request1, admin_user)
        
        # Convert second quote  
        request2 = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_regular_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        invoice2 = convert_quote_to_invoice(db, request2, admin_user)
        
        # Assert unique invoice numbers
        assert invoice1.invoice_number != invoice2.invoice_number
    
    def test_converted_invoice_tax_total_is_zero(
        self,
        db: Session,
        admin_user: User,
        accepted_quote_by_other_user: Quote
    ):
        """
        Test that converted invoices have tax_total set to 0 (per system design).
        """
        # Arrange
        conversion_request = QuoteToInvoiceRequest(
            quote_id=accepted_quote_by_other_user.id,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30)
        )
        
        # Act
        invoice = convert_quote_to_invoice(db, conversion_request, admin_user)
        
        # Assert
        assert invoice.tax_total == Decimal('0.00')