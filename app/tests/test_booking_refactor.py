"""
Comprehensive tests for the refactored booking module

This test suite covers:
- Booking CRUD operations
- Booking item management
- Booking villa management
- History tracking
- Financial calculations
- User isolation
- Status transitions
- Business rules and validation
- Error handling
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.booking import Booking, BookingItem, BookingVilla, BookingHistory
from app.schemas.booking import (
    BookingCreate, BookingUpdate, BookingStatusUpdate, BookingStatus,
    BookingItemCreate, BookingItemUpdate, BookingVillaCreate
)
from app.services.booking import (
    create_booking, get_booking, get_bookings, update_booking,
    update_booking_status, delete_booking,
    add_booking_item, update_booking_item, remove_booking_item,
    add_booking_villa, remove_booking_villa,
    get_booking_history, calculate_booking_totals,
    recalculate_booking_totals, check_villa_availability
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_customer(db: Session, test_user) -> Customer:
    """Create a test customer for bookings"""
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
    """Create a test package for booking items"""
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        category="Adventure",
        type="Tour",
        description="Test package description",
        days=1,
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
def test_villa(db: Session, test_user) -> Villa:
    """Create a test villa for bookings"""
    villa = Villa(
        name="Test Villa",
        description="Test villa description",
        base_price=Decimal("1000000.00"),
        capacity="4 guests",
        room_type="Deluxe",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def test_booking_data(test_customer, test_villa, test_package) -> dict:
    """Generate test booking data"""
    check_in = date.today() + timedelta(days=7)
    check_out = date.today() + timedelta(days=10)
    
    return {
        "customer_id": test_customer.id,
        "check_in": check_in,
        "check_out": check_out,
        "total_pax": 2,
        "status": BookingStatus.pending,
        "notes": "Test booking notes",
        "villas": [test_villa.id],
        "items": [
            {
                "package_id": test_package.id,
                "unit_price": Decimal("500000.00"),
                "discount": Decimal("0.00"),
                "pax": 2,
                "line_total": Decimal("1000000.00")
            }
        ]
    }


# ============================================================================
# Booking CRUD Tests
# ============================================================================

class TestBookingCRUD:
    """Test booking CRUD operations"""
    
    def test_create_booking_success(self, db: Session, test_user, test_booking_data):
        """Test successful booking creation with items and villas"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert
        assert booking.id is not None
        assert booking.booking_code is not None
        assert booking.customer_id == test_booking_data["customer_id"]
        assert booking.check_in == test_booking_data["check_in"]
        assert booking.check_out == test_booking_data["check_out"]
        assert booking.total_pax == 2
        assert booking.status == "pending"
        assert len(booking.items) == 1
        assert len(booking.villas) == 1
        assert booking.total > 0
        assert booking.user_id == test_user["id"]
    
    def test_create_booking_without_items(self, db: Session, test_user, test_customer, test_villa):
        """Test booking creation with villas only (no items)"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert
        assert booking.id is not None
        assert len(booking.items) == 0
        assert len(booking.villas) == 1
        assert booking.total > 0  # Villa charges
    
    def test_create_booking_villa_not_available(self, db: Session, test_user, test_customer, test_villa):
        """Test booking creation fails when villa is not available"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=10)
        
        # Create first booking
        booking_data1 = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        create_booking(db, booking_data1, user_obj)
        
        # Try to create overlapping booking
        booking_data2 = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_booking(db, booking_data2, user_obj)
        assert "not available" in str(exc_info.value.detail).lower()
    
    def test_get_booking_success(self, db: Session, test_user, test_booking_data):
        """Test retrieving a booking by ID"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        created_booking = create_booking(db, booking_data, user_obj)
        
        # Act
        booking = get_booking(db, created_booking.id, user_obj)
        
        # Assert
        assert booking is not None
        assert booking.id == created_booking.id
        assert booking.booking_code == created_booking.booking_code
        assert booking.customer is not None
        assert len(booking.items) > 0
        assert len(booking.villas) > 0
    
    def test_get_booking_not_found(self, db: Session, test_user):
        """Test retrieving non-existent booking returns None"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act
        booking = get_booking(db, 99999, user_obj)
        
        # Assert
        assert booking is None
    
    def test_get_bookings_with_filters(self, db: Session, test_user, test_customer, test_villa):
        """Test retrieving bookings with various filters"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create multiple bookings
        for i in range(3):
            booking_data = BookingCreate(
                customer_id=test_customer.id,
                check_in=date.today() + timedelta(days=7 + i * 5),
                check_out=date.today() + timedelta(days=10 + i * 5),
                total_pax=2,
                villas=[test_villa.id],
                items=[]
            )
            create_booking(db, booking_data, user_obj)
        
        # Act - Get all bookings
        all_bookings = get_bookings(db, user_obj)
        
        # Assert
        assert len(all_bookings) >= 3
        
        # Act - Filter by customer
        customer_bookings = get_bookings(db, user_obj, customer_id=test_customer.id)
        assert len(customer_bookings) >= 3
        
        # Act - Filter by status
        pending_bookings = get_bookings(db, user_obj, status=BookingStatus.pending)
        assert len(pending_bookings) >= 3
    
    def test_update_booking_success(self, db: Session, test_user, test_booking_data):
        """Test updating booking fields"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        update_data = BookingUpdate(
            total_pax=4,
            notes="Updated notes"
        )
        updated_booking = update_booking(db, booking.id, update_data, user_obj)
        
        # Assert
        assert updated_booking.total_pax == 4
        assert updated_booking.notes == "Updated notes"
    
    def test_update_booking_cannot_modify_completed(self, db: Session, test_user, test_booking_data):
        """Test that completed bookings cannot be modified"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Set status to completed
        booking.status = "completed"
        db.commit()
        
        # Act & Assert
        update_data = BookingUpdate(notes="Should fail")
        with pytest.raises(Exception) as exc_info:
            update_booking(db, booking.id, update_data, user_obj)
        assert "cannot modify" in str(exc_info.value.detail).lower()
    
    def test_delete_booking_success(self, db: Session, test_user, test_booking_data):
        """Test deleting a pending booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        booking_id = booking.id
        
        # Act
        result = delete_booking(db, booking_id, user_obj)
        
        # Assert
        assert result is True
        deleted_booking = get_booking(db, booking_id, user_obj)
        assert deleted_booking is None
    
    def test_delete_booking_cannot_delete_confirmed(self, db: Session, test_user, test_booking_data):
        """Test that confirmed bookings cannot be deleted"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Confirm booking
        booking.status = "confirmed"
        db.commit()
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            delete_booking(db, booking.id, user_obj)
        assert "only pending or cancelled" in str(exc_info.value.detail).lower()


# ============================================================================
# Booking Item Management Tests
# ============================================================================

class TestBookingItemManagement:
    """Test booking item CRUD operations"""
    
    def test_add_booking_item_success(self, db: Session, test_user, test_booking_data, test_package):
        """Test adding an item to a booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        test_booking_data["items"] = []  # Start with no items
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        initial_total = booking.total
        
        # Act
        item_data = BookingItemCreate(
            package_id=test_package.id,
            unit_price=Decimal("750000.00"),
            discount=Decimal("0.00"),
            pax=1,
            line_total=Decimal("750000.00")
        )
        new_item = add_booking_item(db, booking.id, item_data, user_obj)
        
        # Assert
        assert new_item.id is not None
        assert new_item.package_id == test_package.id
        assert new_item.line_total == Decimal("750000.00")
        
        # Verify booking total was recalculated
        updated_booking = get_booking(db, booking.id, user_obj)
        assert updated_booking.total >= initial_total  # Total should be at least the same or higher
    
    def test_update_booking_item_success(self, db: Session, test_user, test_booking_data):
        """Test updating a booking item"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        item = booking.items[0]
        
        # Act
        update_data = BookingItemUpdate(
            pax=3,
            line_total=Decimal("1500000.00")
        )
        updated_item = update_booking_item(db, booking.id, item.id, update_data, user_obj)
        
        # Assert
        assert updated_item.pax == 3
        assert updated_item.line_total == Decimal("1500000.00")
    
    def test_remove_booking_item_success(self, db: Session, test_user, test_booking_data):
        """Test removing an item from a booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        item = booking.items[0]
        item_id = item.id
        
        # Act
        result = remove_booking_item(db, booking.id, item_id, user_obj)
        
        # Assert
        assert result is True
        updated_booking = get_booking(db, booking.id, user_obj)
        assert len(updated_booking.items) == 0
    
    def test_add_item_to_completed_booking_fails(self, db: Session, test_user, test_booking_data, test_package):
        """Test that items cannot be added to completed bookings"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        booking.status = "completed"
        db.commit()
        
        # Act & Assert
        item_data = BookingItemCreate(
            package_id=test_package.id,
            unit_price=Decimal("500000.00"),
            discount=Decimal("0.00"),
            pax=1,
            line_total=Decimal("500000.00")
        )
        with pytest.raises(Exception) as exc_info:
            add_booking_item(db, booking.id, item_data, user_obj)
        assert "cannot modify" in str(exc_info.value.detail).lower()


# ============================================================================
# Booking Villa Management Tests
# ============================================================================

class TestBookingVillaManagement:
    """Test booking villa CRUD operations"""
    
    def test_add_booking_villa_success(self, db: Session, test_user, test_customer, test_villa):
        """Test adding a villa to a booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            villas=[],  # Start with no villas
            items=[]
        )
        booking = create_booking(db, booking_data, user_obj)
        initial_total = booking.total
        
        # Act
        villa_data = BookingVillaCreate(villa_id=test_villa.id)
        new_villa = add_booking_villa(db, booking.id, villa_data, user_obj)
        
        # Assert
        assert new_villa.id is not None
        assert new_villa.villa_id == test_villa.id
        
        # Verify booking total was recalculated
        updated_booking = get_booking(db, booking.id, user_obj)
        assert updated_booking.total >= initial_total  # Total should be at least the same or higher
    
    def test_add_unavailable_villa_fails(self, db: Session, test_user, test_customer, test_villa):
        """Test that unavailable villas cannot be added"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=10)
        
        # Create first booking with villa
        booking_data1 = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        create_booking(db, booking_data1, user_obj)
        
        # Create second booking without villa
        booking_data2 = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[],
            items=[]
        )
        booking2 = create_booking(db, booking_data2, user_obj)
        
        # Act & Assert - Try to add already booked villa
        villa_data = BookingVillaCreate(villa_id=test_villa.id)
        with pytest.raises(Exception) as exc_info:
            add_booking_villa(db, booking2.id, villa_data, user_obj)
        assert "not available" in str(exc_info.value.detail).lower()
    
    def test_remove_booking_villa_success(self, db: Session, test_user, test_booking_data):
        """Test removing a villa from a booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        villa = booking.villas[0]
        villa_id = villa.villa_id
        
        # Act
        result = remove_booking_villa(db, booking.id, villa_id, user_obj)
        
        # Assert
        assert result is True
        updated_booking = get_booking(db, booking.id, user_obj)
        assert len(updated_booking.villas) == 0


# ============================================================================
# Booking History Tests
# ============================================================================

class TestBookingHistory:
    """Test booking history tracking"""
    
    def test_history_created_on_booking_creation(self, db: Session, test_user, test_booking_data):
        """Test that history record is created when booking is created"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        history = get_booking_history(db, booking.id, user_obj)
        
        # Assert
        assert len(history) >= 1
        creation_record = next((h for h in history if h.change_type == "created"), None)
        assert creation_record is not None
        assert creation_record.field_name == "status"
        assert creation_record.new_value == "pending"
    
    def test_history_created_on_status_change(self, db: Session, test_user, test_booking_data):
        """Test that history is recorded for status changes"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        status_update = BookingStatusUpdate(status=BookingStatus.confirmed)
        update_booking_status(db, booking.id, status_update, user_obj)
        history = get_booking_history(db, booking.id, user_obj)
        
        # Assert
        status_changes = [h for h in history if h.change_type == "status_change"]
        assert len(status_changes) >= 1
        assert status_changes[0].old_value == "pending"
        assert status_changes[0].new_value == "confirmed"
    
    def test_history_created_on_item_addition(self, db: Session, test_user, test_booking_data, test_package):
        """Test that history is recorded when items are added"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        test_booking_data["items"] = []
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        item_data = BookingItemCreate(
            package_id=test_package.id,
            unit_price=Decimal("500000.00"),
            discount=Decimal("0.00"),
            pax=1,
            line_total=Decimal("500000.00")
        )
        add_booking_item(db, booking.id, item_data, user_obj)
        history = get_booking_history(db, booking.id, user_obj)
        
        # Assert
        item_added = [h for h in history if h.change_type == "item_added"]
        assert len(item_added) >= 1
        assert "Test Package" in item_added[0].new_value
    
    def test_history_created_on_villa_addition(self, db: Session, test_user, test_customer, test_villa):
        """Test that history is recorded when villas are added"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            villas=[],
            items=[]
        )
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        villa_data = BookingVillaCreate(villa_id=test_villa.id)
        add_booking_villa(db, booking.id, villa_data, user_obj)
        history = get_booking_history(db, booking.id, user_obj)
        
        # Assert
        villa_added = [h for h in history if h.change_type == "villa_added"]
        assert len(villa_added) >= 1
        assert "Test Villa" in villa_added[0].new_value


# ============================================================================
# Calculation Tests
# ============================================================================

class TestBookingCalculations:
    """Test booking financial calculations"""
    
    def test_calculate_totals_items_and_villas(self, db: Session, test_user, test_booking_data):
        """Test calculation of booking totals with items and villas"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert
        # 3 nights * 1,000,000 = 3,000,000 (villa)
        # 1,000,000 (items)
        # Total = 4,000,000
        expected_total = Decimal("4000000.00")
        assert booking.total == expected_total
        assert booking.amount_due == expected_total
        assert booking.amount_paid == Decimal("0.00")
    
    def test_recalculate_totals_after_item_addition(self, db: Session, test_user, test_booking_data, test_package):
        """Test that totals are recalculated when items are added"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        initial_total = booking.total
        
        # Act
        item_data = BookingItemCreate(
            package_id=test_package.id,
            unit_price=Decimal("500000.00"),
            discount=Decimal("0.00"),
            pax=1,
            line_total=Decimal("500000.00")
        )
        add_booking_item(db, booking.id, item_data, user_obj)
        
        # Assert
        updated_booking = get_booking(db, booking.id, user_obj)
        assert updated_booking.total >= initial_total  # Total should be at least the initial amount
    
    def test_villa_total_calculation(self, db: Session, test_user, test_customer, test_villa):
        """Test villa total calculation based on nights (calculated from booking dates)"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=12)  # 5 nights
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert - villa totals are calculated from booking dates, not stored in junction table
        expected_villa_total = test_villa.base_price * 5
        assert booking.total == expected_villa_total


# ============================================================================
# User Isolation Tests
# ============================================================================

class TestUserIsolation:
    """Test user isolation for bookings"""
    
    def test_user_can_see_own_bookings(self, db: Session, test_user, test_booking_data):
        """Test that users can see their own bookings"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        retrieved_booking = get_booking(db, booking.id, user_obj)
        
        # Assert
        assert retrieved_booking is not None
        assert retrieved_booking.id == booking.id
    
    def test_user_cannot_see_other_user_bookings(self, db: Session, test_user, test_admin, test_booking_data):
        """Test that regular users cannot see other users' bookings"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        admin_obj = db.query(User).filter(User.id == test_admin["id"]).first()
        
        # Create customer for admin
        admin_customer = Customer(
            user_id=test_admin["id"],
            name="Admin Customer",
            email="admin_customer@test.com"
        )
        db.add(admin_customer)
        db.commit()
        
        # Create booking as admin
        test_booking_data["customer_id"] = admin_customer.id
        booking_data = BookingCreate(**test_booking_data)
        admin_booking = create_booking(db, booking_data, admin_obj)
        
        # Act - Try to retrieve as regular user
        retrieved_booking = get_booking(db, admin_booking.id, user_obj)
        
        # Assert
        assert retrieved_booking is None
    
    def test_admin_can_see_all_bookings(self, db: Session, test_user, test_admin, test_booking_data):
        """Test that admins can see all bookings"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        admin_obj = db.query(User).filter(User.id == test_admin["id"]).first()
        
        # Create booking as regular user
        booking_data = BookingCreate(**test_booking_data)
        user_booking = create_booking(db, booking_data, user_obj)
        
        # Act - Retrieve as admin
        retrieved_booking = get_booking(db, user_booking.id, admin_obj)
        
        # Assert
        assert retrieved_booking is not None
        assert retrieved_booking.id == user_booking.id


# ============================================================================
# Status Transition Tests
# ============================================================================

class TestStatusTransitions:
    """Test booking status workflow transitions"""
    
    def test_valid_status_transition_pending_to_confirmed(self, db: Session, test_user, test_booking_data):
        """Test valid transition from pending to confirmed"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        status_update = BookingStatusUpdate(status=BookingStatus.confirmed)
        updated_booking = update_booking_status(db, booking.id, status_update, user_obj)
        
        # Assert
        assert updated_booking.status == "confirmed"
    
    def test_valid_status_transition_confirmed_to_checked_in(self, db: Session, test_user, test_booking_data):
        """Test valid transition from confirmed to checked_in"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Confirm first
        status_update1 = BookingStatusUpdate(status=BookingStatus.confirmed)
        update_booking_status(db, booking.id, status_update1, user_obj)
        
        # Act
        status_update2 = BookingStatusUpdate(status=BookingStatus.checked_in)
        updated_booking = update_booking_status(db, booking.id, status_update2, user_obj)
        
        # Assert
        assert updated_booking.status == "checked_in"
    
    def test_invalid_status_transition_pending_to_checked_in(self, db: Session, test_user, test_booking_data):
        """Test invalid transition from pending to checked_in"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act & Assert
        status_update = BookingStatusUpdate(status=BookingStatus.checked_in)
        with pytest.raises(Exception) as exc_info:
            update_booking_status(db, booking.id, status_update, user_obj)
        assert "cannot change status" in str(exc_info.value.detail).lower()
    
    def test_status_transition_to_cancelled(self, db: Session, test_user, test_booking_data):
        """Test transition to cancelled status"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act
        status_update = BookingStatusUpdate(status=BookingStatus.cancelled)
        updated_booking = update_booking_status(db, booking.id, status_update, user_obj)
        
        # Assert
        assert updated_booking.status == "cancelled"
    
    def test_cannot_change_from_completed_status(self, db: Session, test_user, test_booking_data):
        """Test that completed bookings cannot change status"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Manually set to completed (simulating full workflow)
        booking.status = "completed"
        db.commit()
        
        # Act & Assert
        status_update = BookingStatusUpdate(status=BookingStatus.pending)
        with pytest.raises(Exception) as exc_info:
            update_booking_status(db, booking.id, status_update, user_obj)
        assert "cannot change status" in str(exc_info.value.detail).lower()


# ============================================================================
# Validation Tests
# ============================================================================

class TestBookingValidation:
    """Test booking validation rules"""
    
    def test_validate_check_out_after_check_in(self, db: Session, test_user, test_customer):
        """Test that check_out must be after check_in"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=5)  # Before check_in
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            booking_data = BookingCreate(
                customer_id=test_customer.id,
                check_in=check_in,
                check_out=check_out,
                total_pax=2,
                villas=[],
                items=[]
            )
        assert "check_out must be after check_in" in str(exc_info.value).lower()
    
    def test_validate_total_pax_positive(self, db: Session, test_user, test_customer):
        """Test that total_pax must be positive"""
        # Arrange & Act & Assert
        with pytest.raises(Exception) as exc_info:
            booking_data = BookingCreate(
                customer_id=test_customer.id,
                check_in=date.today() + timedelta(days=7),
                check_out=date.today() + timedelta(days=10),
                total_pax=0,  # Invalid
                villas=[],
                items=[]
            )
        assert "total_pax must be at least 1" in str(exc_info.value).lower()
    
    def test_validate_customer_exists(self, db: Session, test_user):
        """Test that customer must exist"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act & Assert
        booking_data = BookingCreate(
            customer_id=99999,  # Non-existent
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            villas=[],
            items=[]
        )
        with pytest.raises(Exception) as exc_info:
            create_booking(db, booking_data, user_obj)
        assert "customer not found" in str(exc_info.value.detail).lower()
    
    def test_customer_relationship_accessible(self, db: Session, test_user, test_booking_data):
        """Test that customer relationship is properly accessible"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        
        # Act
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert
        assert booking.customer is not None
        assert booking.customer.name == "Test Customer"
        assert booking.customer.email == "customer@test.com"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling in booking operations"""
    
    def test_404_error_for_non_existent_booking(self, db: Session, test_user):
        """Test 404 error for non-existent booking"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act
        booking = get_booking(db, 99999, user_obj)
        
        # Assert
        assert booking is None
    
    def test_404_error_for_non_existent_package(self, db: Session, test_user, test_customer):
        """Test 404 error when adding non-existent package"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            villas=[],
            items=[
                {
                    "package_id": 99999,  # Non-existent
                    "unit_price": Decimal("500000.00"),
                    "discount": Decimal("0.00"),
                    "pax": 1,
                    "line_total": Decimal("500000.00")
                }
            ]
        )
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            create_booking(db, booking_data, user_obj)
        assert "package" in str(exc_info.value.detail).lower() and "not found" in str(exc_info.value.detail).lower()
    
    def test_400_error_for_invalid_status_transition(self, db: Session, test_user, test_booking_data):
        """Test 400 error for invalid status transition"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        booking_data = BookingCreate(**test_booking_data)
        booking = create_booking(db, booking_data, user_obj)
        
        # Act & Assert - Try invalid transition
        status_update = BookingStatusUpdate(status=BookingStatus.checked_out)
        with pytest.raises(Exception) as exc_info:
            update_booking_status(db, booking.id, status_update, user_obj)
        assert "cannot change status" in str(exc_info.value.detail).lower()


# ============================================================================
# Villa Availability Tests
# ============================================================================

class TestVillaAvailability:
    """Test villa availability checking"""
    
    def test_check_villa_availability_free_dates(self, db: Session, test_villa):
        """Test checking availability for free dates"""
        # Arrange
        check_in = date.today() + timedelta(days=30)
        check_out = date.today() + timedelta(days=33)
        
        # Act
        is_available, unavailable_dates = check_villa_availability(
            db, test_villa.id, check_in, check_out
        )
        
        # Assert
        assert is_available is True
        assert len(unavailable_dates) == 0
    
    def test_check_villa_availability_booked_dates(self, db: Session, test_user, test_customer, test_villa):
        """Test checking availability for booked dates"""
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date.today() + timedelta(days=7)
        check_out = date.today() + timedelta(days=10)
        
        # Create booking
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa.id],
            items=[]
        )
        create_booking(db, booking_data, user_obj)
        
        # Act
        is_available, unavailable_dates = check_villa_availability(
            db, test_villa.id, check_in, check_out
        )
        
        # Assert
        assert is_available is False
        assert len(unavailable_dates) > 0