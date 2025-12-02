"""
Comprehensive tests for quote update user isolation fix

This test suite verifies the fix for the bug where update_quote() incorrectly
enforced user isolation for all users. After the fix:
- Admin/finance/sales users can update quotes with packages from any user
- Regular users are restricted to their own packages

Test Coverage:
- update_quote() with different user roles and package ownership
- update_quote_status() respects user isolation rules  
- delete_quote() respects user isolation rules
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.quote import Quote, QuoteItem
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate, QuoteStatusUpdate
from app.services.quote import create_quote, update_quote, update_quote_status, delete_quote
from fastapi import HTTPException


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def regular_user(db: Session) -> User:
    """Create a regular user (non-privileged)"""
    user = User(
        username="regular_user",
        email="regular@example.com",
        full_name="Regular User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user"""
    user = User(
        username="admin_user",
        email="admin@example.com",
        full_name="Admin User",
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
    """Create a finance user"""
    user = User(
        username="finance_user",
        email="finance@example.com",
        full_name="Finance User",
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
    """Create a sales user"""
    user = User(
        username="sales_user",
        email="sales@example.com",
        full_name="Sales User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='sales'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: Session) -> User:
    """Create another regular user to test cross-user access"""
    user = User(
        username="other_user",
        email="other@example.com",
        full_name="Other User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def customer_for_regular_user(db: Session, regular_user: User) -> Customer:
    """Create a customer for the regular user"""
    customer = Customer(
        user_id=regular_user.id,
        name="Regular User Customer",
        email="regular.customer@test.com",
        phone_number="6281234567890",
        address="Regular Address",
        billing_address="Regular Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def customer_for_other_user(db: Session, other_user: User) -> Customer:
    """Create a customer for the other user"""
    customer = Customer(
        user_id=other_user.id,
        name="Other User Customer",
        email="other.customer@test.com",
        phone_number="6281234567891",
        address="Other Address",
        billing_address="Other Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def customer_for_admin(db: Session, admin_user: User) -> Customer:
    """Create a customer for the admin user"""
    customer = Customer(
        user_id=admin_user.id,
        name="Admin Customer",
        email="admin.customer@test.com",
        phone_number="6281234567892",
        address="Admin Address",
        billing_address="Admin Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def package_owned_by_regular_user(db: Session, regular_user: User) -> Package:
    """Create a package owned by the regular user"""
    package = Package(
        user_id=regular_user.id,
        name="Regular User Package",
        category="Adventure",
        type="Tour",
        description="Package owned by regular user",
        days=3,
        cost_per_pax=Decimal("400000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@pytest.fixture
def package_owned_by_other_user(db: Session, other_user: User) -> Package:
    """Create a package owned by another user"""
    package = Package(
        user_id=other_user.id,
        name="Other User Package",
        category="Beach",
        type="Resort",
        description="Package owned by other user",
        days=5,
        cost_per_pax=Decimal("400000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@pytest.fixture
def quote_with_other_user_package(
    db: Session,
    regular_user: User,
    customer_for_regular_user: Customer,
    package_owned_by_other_user: Package
) -> Quote:
    """Create a quote for regular user that contains a package from another user"""
    quote_data = QuoteCreate(
        customer_id=customer_for_regular_user.id,
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=12),
        status="draft",
        total=Decimal("40100000"),
        items=[
            QuoteItemCreate(
                package_id=package_owned_by_other_user.id,
                unit_price=Decimal("400000.00"),
                pax=100,
                discount=Decimal("0"),
                line_total=Decimal("40000000.00")
            )
        ]
    )
    # Create the quote as admin to bypass initial isolation checks
    admin = User(
        username="temp_admin",
        email="temp@admin.com",
        full_name="Temp Admin",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='admin'
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    quote = create_quote(db, quote_data, admin)
    # Change the user_id to regular_user after creation
    quote.user_id = regular_user.id
    db.commit()
    db.refresh(quote)
    return quote


# ============================================================================
# Test Cases for update_quote()
# ============================================================================

class TestQuoteUpdateIsolation:
    """Test quote update operations with user isolation"""
    
    def test_admin_can_update_quote_with_any_package(
        self,
        db: Session,
        admin_user: User,
        customer_for_admin: Customer,
        quote_with_other_user_package: Quote,
        package_owned_by_other_user: Package
    ):
        """
        Test that admin user can update a quote with packages from any user.
        
        Admin users should bypass user isolation and be able to update quotes
        with packages created by any user in the system.
        """
        # Arrange - Update payload with package from different user
        update_data = QuoteUpdate(
            customer_id=customer_for_admin.id,
            expiry_date=date.today() + timedelta(days=60),
            status="draft",
            total=Decimal("40100000"),
            check_in=date.today() + timedelta(days=13),
            check_out=date.today() + timedelta(days=14),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        
        # Act - Admin updates quote with package from different user
        updated_quote = update_quote(db, quote_with_other_user_package.id, update_data, admin_user)
        
        # Assert - Update succeeds
        assert updated_quote is not None
        assert updated_quote.id == quote_with_other_user_package.id
        assert updated_quote.customer_id == customer_for_admin.id
        assert len(updated_quote.items) == 1
        assert updated_quote.items[0].package_id == package_owned_by_other_user.id
        assert updated_quote.check_in == date.today() + timedelta(days=13)
        assert updated_quote.check_out == date.today() + timedelta(days=14)
    
    def test_finance_can_update_quote_with_any_package(
        self,
        db: Session,
        finance_user: User,
        customer_for_regular_user: Customer,
        quote_with_other_user_package: Quote,
        package_owned_by_other_user: Package
    ):
        """
        Test that finance user can update a quote with packages from any user.
        
        Finance users should bypass user isolation and be able to update quotes
        with packages created by any user in the system.
        """
        # Arrange - Update payload with package from different user
        update_data = QuoteUpdate(
            expiry_date=date.today() + timedelta(days=45),
            status="draft",
            total=Decimal("40100000"),
            check_in=date.today() + timedelta(days=13),
            check_out=date.today() + timedelta(days=14),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        
        # Act - Finance user updates quote with package from different user
        updated_quote = update_quote(db, quote_with_other_user_package.id, update_data, finance_user)
        
        # Assert - Update succeeds
        assert updated_quote is not None
        assert updated_quote.id == quote_with_other_user_package.id
        assert len(updated_quote.items) == 1
        assert updated_quote.items[0].package_id == package_owned_by_other_user.id
        assert updated_quote.check_in == date.today() + timedelta(days=13)
        assert updated_quote.check_out == date.today() + timedelta(days=14)
    
    def test_sales_can_update_quote_with_any_package(
        self,
        db: Session,
        sales_user: User,
        customer_for_regular_user: Customer,
        quote_with_other_user_package: Quote,
        package_owned_by_other_user: Package
    ):
        """
        Test that sales user can update a quote with packages from any user.
        
        Sales users should bypass user isolation and be able to update quotes
        with packages created by any user in the system.
        """
        # Arrange - Update payload with package from different user
        update_data = QuoteUpdate(
            expiry_date=date.today() + timedelta(days=45),
            status="draft",
            total=Decimal("40100000"),
            check_in=date.today() + timedelta(days=13),
            check_out=date.today() + timedelta(days=14),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        
        # Act - Sales user updates quote with package from different user
        updated_quote = update_quote(db, quote_with_other_user_package.id, update_data, sales_user)
        
        # Assert - Update succeeds
        assert updated_quote is not None
        assert updated_quote.id == quote_with_other_user_package.id
        assert len(updated_quote.items) == 1
        assert updated_quote.items[0].package_id == package_owned_by_other_user.id
        assert updated_quote.check_in == date.today() + timedelta(days=13)
        assert updated_quote.check_out == date.today() + timedelta(days=14)
    
    def test_regular_user_cannot_update_quote_with_other_user_package(
        self,
        db: Session,
        regular_user: User,
        customer_for_regular_user: Customer,
        quote_with_other_user_package: Quote,
        package_owned_by_other_user: Package
    ):
        """
        Test that regular user CANNOT update a quote with packages from another user.
        
        Regular users should be restricted by user isolation and only be able
        to use packages they created themselves.
        """
        # Arrange - Update payload attempting to use package from different user
        update_data = QuoteUpdate(
            expiry_date=date.today() + timedelta(days=45),
            status="draft",
            total=Decimal("40100000"),
            check_in=date.today() + timedelta(days=13),
            check_out=date.today() + timedelta(days=14),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        
        # Act & Assert - Regular user update fails with 404
        with pytest.raises(HTTPException) as exc_info:
            update_quote(db, quote_with_other_user_package.id, update_data, regular_user)
        
        # Assert - Returns 404 (package not found due to isolation)
        assert exc_info.value.status_code == 404
        assert "package" in exc_info.value.detail.lower()
        assert "not found" in exc_info.value.detail.lower()
    
    def test_regular_user_can_update_quote_with_own_package(
        self,
        db: Session,
        regular_user: User,
        customer_for_regular_user: Customer,
        package_owned_by_regular_user: Package
    ):
        """
        Test that regular user CAN update a quote with their own packages.
        
        Regular users should be able to update quotes using packages they
        created themselves.
        """
        # Arrange - Create a quote with user's own package
        quote_data = QuoteCreate(
            customer_id=customer_for_regular_user.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
            status="draft",
            total=Decimal("40100000"),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_regular_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, regular_user)
        
        # Act - Update quote with same user's package
        update_data = QuoteUpdate(
            expiry_date=date.today() + timedelta(days=60),
            status="draft",
            total=Decimal("40100000"),
            check_in=date.today() + timedelta(days=13),
            check_out=date.today() + timedelta(days=14),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_regular_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        updated_quote = update_quote(db, quote.id, update_data, regular_user)
        
        # Assert - Update succeeds
        assert updated_quote is not None
        assert updated_quote.id == quote.id
        assert len(updated_quote.items) == 1
        assert updated_quote.items[0].package_id == package_owned_by_regular_user.id
        assert updated_quote.check_in == date.today() + timedelta(days=13)
        assert updated_quote.check_out == date.today() + timedelta(days=14)


# ============================================================================
# Test Cases for update_quote_status()
# ============================================================================

class TestQuoteStatusUpdateIsolation:
    """Test quote status update operations with user isolation"""
    
    def test_update_quote_status_respects_user_isolation(
        self,
        db: Session,
        admin_user: User,
        regular_user: User,
        other_user: User,
        customer_for_other_user: Customer,
        package_owned_by_other_user: Package
    ):
        """
        Test that update_quote_status() respects user isolation rules.
        
        Admin should be able to update status of any quote.
        Regular user should only be able to update status of their own quotes.
        """
        # Arrange - Create a quote owned by other_user
        quote_data = QuoteCreate(
            customer_id=customer_for_other_user.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
            status="draft",
            total=Decimal("40100000"),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        quote = create_quote(db, quote_data, other_user)
        
        # Test 1: Admin can update status of other_user's quote
        status_update = QuoteStatusUpdate(status="sent")
        updated_quote = update_quote_status(db, quote.id, status_update, admin_user)
        assert updated_quote.status == "sent"
        
        # Test 2: Regular user CANNOT update status of other_user's quote
        status_update = QuoteStatusUpdate(status="accepted")
        with pytest.raises(HTTPException) as exc_info:
            update_quote_status(db, quote.id, status_update, regular_user)
        
        # Assert - Regular user gets 404 (quote not found due to isolation)
        assert exc_info.value.status_code == 404
        assert "quote not found" in exc_info.value.detail.lower()
        
        # Test 3: Owner (other_user) can update status of their own quote
        # From 'sent' we can transition to 'accepted'
        status_update = QuoteStatusUpdate(status="accepted")
        updated_quote = update_quote_status(db, quote.id, status_update, other_user)
        assert updated_quote.status == "accepted"


# ============================================================================
# Test Cases for delete_quote()
# ============================================================================

class TestQuoteDeleteIsolation:
    """Test quote delete operations with user isolation"""
    
    def test_delete_quote_respects_user_isolation(
        self,
        db: Session,
        admin_user: User,
        regular_user: User,
        other_user: User,
        customer_for_other_user: Customer,
        package_owned_by_other_user: Package
    ):
        """
        Test that delete_quote() respects user isolation rules.
        
        Admin should be able to delete any quote.
        Regular user should only be able to delete their own quotes.
        """
        # Arrange - Create two draft quotes, one owned by other_user
        quote_data = QuoteCreate(
            customer_id=customer_for_other_user.id,
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            check_in=date.today() + timedelta(days=10),
            check_out=date.today() + timedelta(days=12),
            status="draft",
            total=Decimal("40100000"),
            items=[
                QuoteItemCreate(
                    package_id=package_owned_by_other_user.id,
                    unit_price=Decimal("400000.00"),
                    pax=100,
                    discount=Decimal("0"),
                    line_total=Decimal("40000000.00")
                )
            ]
        )
        quote1 = create_quote(db, quote_data, other_user)
        quote2 = create_quote(db, quote_data, other_user)
        
        # Test 1: Regular user CANNOT delete other_user's quote
        with pytest.raises(HTTPException) as exc_info:
            delete_quote(db, quote1.id, regular_user)
        
        # Assert - Regular user gets 404 (quote not found due to isolation)
        assert exc_info.value.status_code == 404
        assert "quote not found" in exc_info.value.detail.lower()
        
        # Verify quote still exists
        quote_exists = db.query(Quote).filter(Quote.id == quote1.id).first()
        assert quote_exists is not None
        
        # Test 2: Admin CAN delete other_user's quote
        result = delete_quote(db, quote1.id, admin_user)
        assert result is True
        
        # Verify quote is deleted
        quote_exists = db.query(Quote).filter(Quote.id == quote1.id).first()
        assert quote_exists is None
        
        # Test 3: Owner (other_user) can delete their own quote
        result = delete_quote(db, quote2.id, other_user)
        assert result is True
        
        # Verify quote is deleted
        quote_exists = db.query(Quote).filter(Quote.id == quote2.id).first()
        assert quote_exists is None