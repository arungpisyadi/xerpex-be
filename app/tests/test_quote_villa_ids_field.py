"""
Unit test to verify that 'villa_ids' field is properly accepted and saved to quote_villas table

This test suite covers:
- Creating quotes with 'villa_ids' field (new field name)
- Creating quotes with 'villas' field (backward compatibility)
- Verifying villa associations are correctly saved to quote_villas table
- Testing with the exact payload structure from production use
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.quote import Quote, QuoteVilla
from app.schemas.quote import QuoteCreate, QuoteItemCreate
from app.services.quote import create_quote, delete_quote


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_sales_person(db: Session) -> User:
    """Create a test sales person (user) for quote"""
    sales_user = User(
        username="testsales",
        email="sales@test.com",
        full_name="Test Sales Person",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        is_active=True,
        role='user'
    )
    db.add(sales_user)
    db.commit()
    db.refresh(sales_user)
    return sales_user


@pytest.fixture
def test_customer_for_villa_ids(db: Session, test_user) -> Customer:
    """Create a test customer for villa_ids testing"""
    customer = Customer(
        user_id=test_user["id"],
        name="Villa IDs Test Customer",
        email="villaidscustomer@test.com",
        phone_number="6281234567890",
        address="Test Address for Villa IDs",
        billing_address="Test Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_packages_for_villa_ids(db: Session, test_user) -> tuple:
    """Create test packages for villa_ids testing"""
    package1 = Package(
        user_id=test_user["id"],
        name="Adventure Package",
        category="Adventure",
        type="Tour",
        description="Adventure package for testing",
        days=2,
        cost_per_pax=Decimal("400000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    package2 = Package(
        user_id=test_user["id"],
        name="Premium Package",
        category="Premium",
        type="Tour",
        description="Premium package for testing",
        days=3,
        cost_per_pax=Decimal("800000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package1)
    db.add(package2)
    db.commit()
    db.refresh(package1)
    db.refresh(package2)
    return (package1, package2)


@pytest.fixture
def test_villas_for_ids(db: Session) -> tuple:
    """Create test villas for villa_ids testing"""
    villa1 = Villa(
        name="Villa ID Test 1",
        description="First villa for villa_ids testing",
        base_price=Decimal("1200000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True
    )
    villa2 = Villa(
        name="Villa ID Test 2",
        description="Second villa for villa_ids testing",
        base_price=Decimal("1800000.00"),
        capacity="6 guests",
        room_type="Premium",
        is_active=True
    )
    db.add(villa1)
    db.add(villa2)
    db.commit()
    db.refresh(villa1)
    db.refresh(villa2)
    return (villa1, villa2)


# ============================================================================
# Test Cases
# ============================================================================

class TestQuoteVillaIdsField:
    """Test suite for villa_ids field acceptance and storage"""
    
    def test_create_quote_with_villa_ids_field(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_villas_for_ids,
        test_sales_person
    ):
        """
        Test creating a quote using 'villa_ids' field (new field name)
        Verifies that villa associations are correctly saved to quote_villas table
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, package2 = test_packages_for_villa_ids
        villa1, villa2 = test_villas_for_ids
        
        # Use exact payload structure from user with villa_ids field
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("4400000"),
            check_in=date(2025, 12, 12),
            check_out=date(2025, 12, 14),
            villa_ids=[villa1.id, villa2.id],  # Using villa_ids field
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                ),
                QuoteItemCreate(
                    package_id=package2.id,
                    unit_price=Decimal("800000"),
                    discount=Decimal("0"),
                    pax=3,
                    line_total=Decimal("2400000")
                )
            ]
        )
        
        # Act - Create quote using service
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Quote was created
        assert quote.id is not None
        assert quote.customer_id == test_customer_for_villa_ids.id
        assert quote.sales_person_id == test_sales_person.id
        assert quote.status == "draft"
        
        # Assert - Query database to verify villa associations in quote_villas table
        quote_villas = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote.id).all()
        
        # Assert - 2 QuoteVilla records created
        assert len(quote_villas) == 2, f"Expected 2 QuoteVilla records, found {len(quote_villas)}"
        
        # Assert - Correct villa IDs are associated
        villa_ids_in_db = [qv.villa_id for qv in quote_villas]
        assert villa1.id in villa_ids_in_db, f"Villa {villa1.id} not found in quote_villas"
        assert villa2.id in villa_ids_in_db, f"Villa {villa2.id} not found in quote_villas"
        
        # Assert - Villa relationships are accessible
        for qv in quote_villas:
            assert qv.villa is not None
            assert qv.villa.name in ["Villa ID Test 1", "Villa ID Test 2"]
        
        # Assert - Quote includes villas
        assert len(quote.villas) == 2
    
    def test_create_quote_with_villas_field_backward_compatibility(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_villas_for_ids,
        test_sales_person
    ):
        """
        Test creating a quote using 'villas' field (old field name)
        Verifies backward compatibility is maintained
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, package2 = test_packages_for_villa_ids
        villa1, villa2 = test_villas_for_ids
        
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("4400000"),
            check_in=date(2025, 12, 12),
            check_out=date(2025, 12, 14),
            villas=[villa1.id, villa2.id],  # Using old 'villas' field name
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                ),
                QuoteItemCreate(
                    package_id=package2.id,
                    unit_price=Decimal("800000"),
                    discount=Decimal("0"),
                    pax=3,
                    line_total=Decimal("2400000")
                )
            ]
        )
        
        # Act - Create quote using service
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Query database to verify villa associations
        quote_villas = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote.id).all()
        
        # Assert - Villa associations are correctly saved
        assert len(quote_villas) == 2
        villa_ids_in_db = [qv.villa_id for qv in quote_villas]
        assert villa1.id in villa_ids_in_db
        assert villa2.id in villa_ids_in_db
    
    def test_quote_villas_table_structure(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_villas_for_ids,
        test_sales_person
    ):
        """
        Test the structure and relationships of quote_villas table
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, _ = test_packages_for_villa_ids
        villa1, villa2 = test_villas_for_ids
        
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("2400000"),
            villa_ids=[villa1.id, villa2.id],
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Verify QuoteVilla table structure
        quote_villas = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote.id).all()
        
        for qv in quote_villas:
            # Assert - Has ID field
            assert qv.id is not None
            
            # Assert - Has quote_id foreign key
            assert qv.quote_id == quote.id
            
            # Assert - Has villa_id foreign key
            assert qv.villa_id in [villa1.id, villa2.id]
            
            # Assert - Relationship to Quote works
            assert qv.quote is not None
            assert qv.quote.id == quote.id
            
            # Assert - Relationship to Villa works
            assert qv.villa is not None
            assert qv.villa.id in [villa1.id, villa2.id]
    
    def test_villa_ids_field_with_empty_list(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_sales_person
    ):
        """
        Test creating a quote with empty villa_ids list
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, _ = test_packages_for_villa_ids
        
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("2000000"),
            villa_ids=[],  # Empty villa_ids
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - No QuoteVilla records created
        quote_villas = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote.id).all()
        assert len(quote_villas) == 0
    
    def test_villa_ids_field_with_single_villa(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_villas_for_ids,
        test_sales_person
    ):
        """
        Test creating a quote with single villa in villa_ids
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, _ = test_packages_for_villa_ids
        villa1, _ = test_villas_for_ids
        
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("2000000"),
            villa_ids=[villa1.id],  # Single villa
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                )
            ]
        )
        
        # Act
        quote = create_quote(db, quote_data, user_obj)
        
        # Assert - Single QuoteVilla record created
        quote_villas = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote.id).all()
        assert len(quote_villas) == 1
        assert quote_villas[0].villa_id == villa1.id
    
    def test_villa_ids_cascade_delete(
        self,
        db: Session,
        test_user,
        test_customer_for_villa_ids,
        test_packages_for_villa_ids,
        test_villas_for_ids,
        test_sales_person
    ):
        """
        Test that QuoteVilla records are cascade deleted when quote is deleted
        """
        # Arrange - Create quote with villas
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        package1, _ = test_packages_for_villa_ids
        villa1, villa2 = test_villas_for_ids
        
        quote_data = QuoteCreate(
            customer_id=test_customer_for_villa_ids.id,
            sales_person_id=test_sales_person.id,
            issue_date=date(2025, 11, 28),
            expiry_date=date(2025, 12, 5),
            status="draft",
            total=Decimal("2000000"),
            villa_ids=[villa1.id, villa2.id],
            items=[
                QuoteItemCreate(
                    package_id=package1.id,
                    unit_price=Decimal("400000"),
                    discount=Decimal("0"),
                    pax=5,
                    line_total=Decimal("2000000")
                )
            ]
        )
        
        quote = create_quote(db, quote_data, user_obj)
        quote_id = quote.id
        
        # Verify QuoteVilla records exist
        quote_villas_before = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).count()
        assert quote_villas_before == 2
        
        # Act - Delete quote
        delete_quote(db, quote_id, test_user["id"])
        
        # Assert - QuoteVilla records are cascade deleted
        quote_villas_after = db.query(QuoteVilla).filter(QuoteVilla.quote_id == quote_id).count()
        assert quote_villas_after == 0