"""
Comprehensive tests for booking deletion and villa availability cleanup

This test suite verifies that when bookings are deleted, the villa_availability
entries are properly cleaned up, releasing the villas back to available status.

Test Coverage:
1. Deleting a pending booking with single villa releases availability
2. Deleting a cancelled booking with single villa releases availability
3. Deleting a booking with multiple villas releases all villa availabilities
4. Deleting a booking does not affect other bookings' villa availability
5. Deleting a booking with overlapping date handling
6. Deleting a same-day booking (edge case)
7. Attempting to delete confirmed/completed bookings (negative test)

Each test includes direct database verification of the villa_availability table.
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.user import User
from app.models.customer import Customer
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking
from app.schemas.booking import BookingCreate
from app.services.booking import create_booking, delete_booking


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user matching the test credentials"""
    user = User(
        username="admin@tugugroup.co.id",
        email="admin@tugugroup.co.id",
        full_name="Admin User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: 1q2w3e4r5t
        is_active=True,
        role='admin'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_customer(db: Session, admin_user: User) -> Customer:
    """Create a test customer for booking deletion tests"""
    customer = Customer(
        user_id=admin_user.id,
        name="Deletion Test Customer",
        email="deletion_test@tugugroup.co.id",
        phone_number="6281234567890",
        address="Test Address for Deletion Tests"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def villa_alpha(db: Session) -> Villa:
    """Create test villa Alpha"""
    villa = Villa(
        name="Villa Alpha - Deletion Test",
        description="Test villa Alpha for deletion tests",
        base_price=Decimal("3000000.00"),
        capacity="8 guests",
        room_type="Luxury",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def villa_beta(db: Session) -> Villa:
    """Create test villa Beta"""
    villa = Villa(
        name="Villa Beta - Deletion Test",
        description="Test villa Beta for deletion tests",
        base_price=Decimal("2500000.00"),
        capacity="6 guests",
        room_type="Deluxe",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


@pytest.fixture
def villa_gamma(db: Session) -> Villa:
    """Create test villa Gamma"""
    villa = Villa(
        name="Villa Gamma - Deletion Test",
        description="Test villa Gamma for deletion tests",
        base_price=Decimal("2000000.00"),
        capacity="4 guests",
        room_type="Standard",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# Helper Functions
# ============================================================================

def get_blocked_dates(db: Session, villa_id: int) -> list:
    """Get all blocked dates for a villa from villa_availability table"""
    blocked_records = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.is_available == False
    ).order_by(VillaAvailability.date).all()
    
    return [(record.date, record.blocked_reason) for record in blocked_records]


def verify_date_blocked(db: Session, villa_id: int, check_date: date, booking_code: str) -> bool:
    """Verify a specific date is blocked for a villa with the correct booking code"""
    availability = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.date == check_date
    ).first()
    
    if not availability:
        return False
    
    return (
        availability.is_available is False and
        booking_code in availability.blocked_reason
    )


def verify_date_available(db: Session, villa_id: int, check_date: date) -> bool:
    """Verify a specific date is available (either no record or is_available=True)"""
    availability = db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id,
        VillaAvailability.date == check_date
    ).first()
    
    # No record means available (default state)
    if not availability:
        return True
    
    # Record exists but marked as available
    return availability.is_available is True


def get_availability_count(db: Session, villa_id: int) -> int:
    """Get total count of villa_availability records for a villa"""
    return db.query(VillaAvailability).filter(
        VillaAvailability.villa_id == villa_id
    ).count()


# ============================================================================
# Test 1: Delete Pending Booking with Single Villa
# ============================================================================

class TestDeletePendingBookingSingleVilla:
    """Test that deleting a pending booking releases villa availability"""
    
    def test_delete_pending_booking_releases_single_villa(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify that deleting a pending booking properly releases villa availability.
        
        Scenario:
        - Create pending booking: March 10 - March 15 (5 nights)
        - Verify March 10-14 are blocked
        - Delete the booking
        - Verify March 10-14 are now available (no records)
        - Verify March 15 (checkout) remains available
        
        Expected:
        - All villa_availability entries for the booking are deleted
        - Villa is fully available again
        """
        # Arrange - Create pending booking
        check_in = date(2026, 3, 10)
        check_out = date(2026, 3, 15)
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=6,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking = create_booking(db, booking_data, admin_user)
        booking_code = booking.booking_code
        
        # Verify initial state - villa is blocked
        for day_offset in range(5):
            check_date = check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_code), \
                f"Date {check_date} should be blocked before deletion"
        
        # Verify villa_availability table has 5 records
        initial_count = get_availability_count(db, villa_alpha.id)
        assert initial_count == 5, f"Expected 5 availability records, found {initial_count}"
        
        # Act - Delete the booking
        result = delete_booking(db, booking.id, admin_user)
        assert result is True, "Booking deletion should succeed"
        
        # Assert - Verify all dates are now available (no records)
        for day_offset in range(5):
            check_date = check_in + timedelta(days=day_offset)
            assert verify_date_available(db, villa_alpha.id, check_date), \
                f"Date {check_date} should be available after deletion"
        
        # Assert - Verify villa_availability table has 0 records for this villa
        final_count = get_availability_count(db, villa_alpha.id)
        assert final_count == 0, \
            f"Expected 0 availability records after deletion, found {final_count}"
        
        # Assert - Verify checkout date remains available
        assert verify_date_available(db, villa_alpha.id, check_out), \
            f"Checkout date {check_out} should remain available"
        
        # Assert - Verify booking is deleted from database
        deleted_booking = db.query(Booking).filter(Booking.id == booking.id).first()
        assert deleted_booking is None, "Booking should be deleted from database"


# ============================================================================
# Test 2: Delete Cancelled Booking with Single Villa
# ============================================================================

class TestDeleteCancelledBookingSingleVilla:
    """Test that deleting a cancelled booking releases villa availability"""
    
    def test_delete_cancelled_booking_releases_single_villa(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify that deleting a cancelled booking properly releases villa availability.
        
        Scenario:
        - Create cancelled booking: March 20 - March 25 (5 nights)
        - Verify March 20-24 are blocked
        - Delete the booking
        - Verify March 20-24 are now available (no records)
        
        Expected:
        - All villa_availability entries are deleted
        - Villa is fully available
        """
        # Arrange - Create cancelled booking
        check_in = date(2026, 3, 20)
        check_out = date(2026, 3, 25)
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=4,
            villas=[villa_alpha.id],
            items=[],
            status="cancelled"
        )
        booking = create_booking(db, booking_data, admin_user)
        booking_code = booking.booking_code
        
        # Verify initial state - villa is blocked
        initial_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(initial_blocked) == 5, \
            f"Expected 5 blocked dates initially, found {len(initial_blocked)}"
        
        # Act - Delete the booking
        result = delete_booking(db, booking.id, admin_user)
        assert result is True
        
        # Assert - Verify all dates are now available
        for day_offset in range(5):
            check_date = check_in + timedelta(days=day_offset)
            assert verify_date_available(db, villa_alpha.id, check_date), \
                f"Date {check_date} should be available after deletion"
        
        # Assert - Verify no blocked dates remain
        final_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(final_blocked) == 0, \
            f"Expected 0 blocked dates after deletion, found {len(final_blocked)}"


# ============================================================================
# Test 3: Delete Booking with Multiple Villas
# ============================================================================

class TestDeleteBookingMultipleVillas:
    """Test that deleting a booking releases availability for all villas"""
    
    def test_delete_booking_releases_all_villas(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa,
        villa_beta: Villa,
        villa_gamma: Villa
    ):
        """
        Verify that deleting a booking with multiple villas releases all villa availabilities.
        
        Scenario:
        - Create booking with 3 villas: April 1 - April 6 (5 nights)
        - Verify all 3 villas have April 1-5 blocked
        - Delete the booking
        - Verify all 3 villas are now fully available
        
        Expected:
        - All villa_availability entries for all 3 villas are deleted
        - Each villa is independently verifiable as available
        """
        # Arrange - Create booking with 3 villas
        check_in = date(2026, 4, 1)
        check_out = date(2026, 4, 6)
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=12,
            villas=[villa_alpha.id, villa_beta.id, villa_gamma.id],
            items=[],
            status="pending"
        )
        booking = create_booking(db, booking_data, admin_user)
        booking_code = booking.booking_code
        
        # Verify initial state - all 3 villas are blocked
        for villa in [villa_alpha, villa_beta, villa_gamma]:
            blocked_dates = get_blocked_dates(db, villa.id)
            assert len(blocked_dates) == 5, \
                f"Villa {villa.name} should have 5 blocked dates, found {len(blocked_dates)}"
            
            # Verify each date in range is blocked
            for day_offset in range(5):
                check_date = check_in + timedelta(days=day_offset)
                assert verify_date_blocked(db, villa.id, check_date, booking_code), \
                    f"Villa {villa.name} date {check_date} should be blocked"
        
        # Act - Delete the booking
        result = delete_booking(db, booking.id, admin_user)
        assert result is True
        
        # Assert - Verify all 3 villas are now fully available
        for villa in [villa_alpha, villa_beta, villa_gamma]:
            # Check all dates in range are available
            for day_offset in range(5):
                check_date = check_in + timedelta(days=day_offset)
                assert verify_date_available(db, villa.id, check_date), \
                    f"Villa {villa.name} date {check_date} should be available after deletion"
            
            # Verify no blocked dates remain
            blocked_dates = get_blocked_dates(db, villa.id)
            assert len(blocked_dates) == 0, \
                f"Villa {villa.name} should have 0 blocked dates after deletion, found {len(blocked_dates)}"
            
            # Verify no availability records exist
            availability_count = get_availability_count(db, villa.id)
            assert availability_count == 0, \
                f"Villa {villa.name} should have 0 availability records, found {availability_count}"


# ============================================================================
# Test 4: Deleting Booking Does Not Affect Other Bookings
# ============================================================================

class TestDeleteBookingPreservesOtherBookings:
    """Test that deleting one booking doesn't affect other bookings' availability"""
    
    def test_delete_booking_preserves_other_booking_availability(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify that deleting one booking doesn't affect other bookings' villa availability.
        
        Scenario:
        - Create Booking A: April 10 - April 15
        - Create Booking B: April 20 - April 25
        - Delete Booking A
        - Verify Booking B's villa availability is unaffected
        - Verify Booking A's dates are released
        
        Expected:
        - Booking A's dates (April 10-14) are released
        - Booking B's dates (April 20-24) remain blocked
        - No cross-contamination
        """
        # Arrange - Create Booking A
        booking_a_check_in = date(2026, 4, 10)
        booking_a_check_out = date(2026, 4, 15)
        
        booking_a_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=booking_a_check_in,
            check_out=booking_a_check_out,
            total_pax=4,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking_a = create_booking(db, booking_a_data, admin_user)
        booking_a_code = booking_a.booking_code
        
        # Arrange - Create Booking B
        booking_b_check_in = date(2026, 4, 20)
        booking_b_check_out = date(2026, 4, 25)
        
        booking_b_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=booking_b_check_in,
            check_out=booking_b_check_out,
            total_pax=3,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking_b = create_booking(db, booking_b_data, admin_user)
        booking_b_code = booking_b.booking_code
        
        # Verify initial state - both bookings have blocked dates
        # Booking A: April 10-14 (5 dates)
        for day_offset in range(5):
            check_date = booking_a_check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_a_code)
        
        # Booking B: April 20-24 (5 dates)
        for day_offset in range(5):
            check_date = booking_b_check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_b_code)
        
        # Total blocked dates should be 10
        initial_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(initial_blocked) == 10, \
            f"Expected 10 blocked dates initially, found {len(initial_blocked)}"
        
        # Act - Delete Booking A
        result = delete_booking(db, booking_a.id, admin_user)
        assert result is True
        
        # Assert - Verify Booking A's dates (April 10-14) are now available
        for day_offset in range(5):
            check_date = booking_a_check_in + timedelta(days=day_offset)
            assert verify_date_available(db, villa_alpha.id, check_date), \
                f"Booking A date {check_date} should be available after deletion"
        
        # Assert - Verify Booking B's dates (April 20-24) remain blocked
        for day_offset in range(5):
            check_date = booking_b_check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_b_code), \
                f"Booking B date {check_date} should still be blocked"
        
        # Assert - Verify total blocked dates is now 5 (only Booking B)
        final_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(final_blocked) == 5, \
            f"Expected 5 blocked dates after deletion, found {len(final_blocked)}"
        
        # Assert - Verify all remaining blocked dates belong to Booking B
        for blocked_date, blocked_reason in final_blocked:
            assert booking_b_code in blocked_reason, \
                f"Remaining blocked dates should only reference Booking B, found: {blocked_reason}"


# ============================================================================
# Test 5: Delete Booking with Back-to-Back Scenario
# ============================================================================

class TestDeleteBackToBackBooking:
    """Test deletion in back-to-back booking scenarios"""
    
    def test_delete_first_booking_in_back_to_back_sequence(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify proper handling when deleting first booking in back-to-back sequence.
        
        Scenario:
        - Create Booking A: May 1 - May 5
        - Create Booking B: May 5 - May 10 (back-to-back)
        - Delete Booking A
        - Verify May 1-4 are released
        - Verify May 5-9 remain blocked by Booking B
        
        Expected:
        - Only Booking A's dates are released
        - Booking B's dates remain intact
        """
        # Arrange - Create Booking A
        booking_a_check_in = date(2026, 5, 1)
        booking_a_check_out = date(2026, 5, 5)
        
        booking_a_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=booking_a_check_in,
            check_out=booking_a_check_out,
            total_pax=4,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking_a = create_booking(db, booking_a_data, admin_user)
        
        # Arrange - Create Booking B (back-to-back)
        booking_b_check_in = date(2026, 5, 5)
        booking_b_check_out = date(2026, 5, 10)
        
        booking_b_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=booking_b_check_in,
            check_out=booking_b_check_out,
            total_pax=3,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking_b = create_booking(db, booking_b_data, admin_user)
        booking_b_code = booking_b.booking_code
        
        # Verify initial state - May 1-4 (Booking A) and May 5-9 (Booking B) are blocked
        initial_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(initial_blocked) == 9, \
            f"Expected 9 blocked dates initially (4+5), found {len(initial_blocked)}"
        
        # Act - Delete Booking A
        result = delete_booking(db, booking_a.id, admin_user)
        assert result is True
        
        # Assert - Verify May 1-4 are now available
        for day_offset in range(4):
            check_date = booking_a_check_in + timedelta(days=day_offset)
            assert verify_date_available(db, villa_alpha.id, check_date), \
                f"Date {check_date} should be available after deleting Booking A"
        
        # Assert - Verify May 5-9 remain blocked by Booking B
        for day_offset in range(5):
            check_date = booking_b_check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_b_code), \
                f"Date {check_date} should remain blocked by Booking B"
        
        # Assert - Verify total blocked dates is now 5 (only Booking B)
        final_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(final_blocked) == 5, \
            f"Expected 5 blocked dates after deletion, found {len(final_blocked)}"


# ============================================================================
# Test 6: Delete Same-Day Booking (Edge Case)
# ============================================================================

class TestDeleteSameDayBooking:
    """Test deletion of same-day bookings"""
    
    def test_delete_same_day_booking_no_availability_cleanup(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify that deleting a same-day booking works correctly (no availability records).
        
        Scenario:
        - Create same-day booking: June 1 - June 1 (0 nights)
        - Verify no villa_availability records exist
        - Delete the booking
        - Verify still no villa_availability records (nothing to clean up)
        
        Expected:
        - Deletion succeeds without errors
        - No villa_availability operations performed
        """
        # Arrange - Create same-day booking
        same_date = date(2026, 6, 1)
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=same_date,
            check_out=same_date,
            total_pax=2,
            villas=[villa_alpha.id],
            items=[],
            status="pending"
        )
        booking = create_booking(db, booking_data, admin_user)
        
        # Verify no availability records were created
        initial_count = get_availability_count(db, villa_alpha.id)
        assert initial_count == 0, \
            f"Same-day booking should create no availability records, found {initial_count}"
        
        # Act - Delete the same-day booking
        result = delete_booking(db, booking.id, admin_user)
        assert result is True, "Same-day booking deletion should succeed"
        
        # Assert - Verify still no availability records
        final_count = get_availability_count(db, villa_alpha.id)
        assert final_count == 0, \
            f"Should still have no availability records after deletion, found {final_count}"
        
        # Assert - Verify date remains available
        assert verify_date_available(db, villa_alpha.id, same_date), \
            f"Date {same_date} should remain available"


# ============================================================================
# Test 7: Negative Test - Cannot Delete Confirmed/Completed Bookings
# ============================================================================

class TestCannotDeleteConfirmedBookings:
    """Test that confirmed/completed bookings cannot be deleted"""
    
    def test_cannot_delete_confirmed_booking(
        self,
        db: Session,
        admin_user: User,
        test_customer: Customer,
        villa_alpha: Villa
    ):
        """
        Verify that attempting to delete a confirmed booking raises an error.
        
        Scenario:
        - Create confirmed booking: July 1 - July 5
        - Attempt to delete the booking
        - Verify HTTPException is raised
        - Verify booking still exists
        - Verify villa availability remains blocked
        
        Expected:
        - Deletion fails with appropriate error
        - Booking and availability remain intact
        """
        # Arrange - Create confirmed booking
        check_in = date(2026, 7, 1)
        check_out = date(2026, 7, 5)
        
        booking_data = BookingCreate(
            customer_id=test_customer.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=4,
            villas=[villa_alpha.id],
            items=[],
            status="confirmed"
        )
        booking = create_booking(db, booking_data, admin_user)
        booking_code = booking.booking_code
        
        # Verify initial state
        initial_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(initial_blocked) == 4, \
            f"Expected 4 blocked dates initially, found {len(initial_blocked)}"
        
        # Act & Assert - Attempt to delete confirmed booking (should fail)
        with pytest.raises(HTTPException) as exc_info:
            delete_booking(db, booking.id, admin_user)
        
        assert exc_info.value.status_code == 400
        assert "Only pending or cancelled bookings can be deleted" in str(exc_info.value.detail)
        
        # Assert - Verify booking still exists
        existing_booking = db.query(Booking).filter(Booking.id == booking.id).first()
        assert existing_booking is not None, "Booking should still exist after failed deletion"
        assert existing_booking.status == "confirmed"
        
        # Assert - Verify villa availability remains blocked
        for day_offset in range(4):
            check_date = check_in + timedelta(days=day_offset)
            assert verify_date_blocked(db, villa_alpha.id, check_date, booking_code), \
                f"Date {check_date} should remain blocked after failed deletion"
        
        final_blocked = get_blocked_dates(db, villa_alpha.id)
        assert len(final_blocked) == 4, \
            f"Expected 4 blocked dates after failed deletion, found {len(final_blocked)}"
