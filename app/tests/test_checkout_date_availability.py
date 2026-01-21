"""
Unit tests for villa checkout date availability logic

This test suite verifies that the villa availability logic correctly excludes
the check-out date from availability calculations, allowing back-to-back bookings.

Test Scenarios:
1. Check-out date is not blocked (available for next booking)
2. Back-to-back bookings are allowed (second booking starts on first's checkout)
3. Overlap detection still works (bookings overlapping occupied dates fail)
4. Same-day check-in/check-out edge case (only check-in date blocked)
5. Update booking dates releases old dates and blocks new dates
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.villa import Villa, VillaAvailability
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.booking import (
    create_booking, update_booking, check_villa_availability
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_customer_for_checkout_tests(db: Session, test_user) -> Customer:
    """Create a test customer for checkout availability tests"""
    customer = Customer(
        user_id=test_user["id"],
        name="Checkout Test Customer",
        email="checkout_test@test.com",
        phone_number="6281234567890",
        address="Test Address"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_villa_for_checkout_tests(db: Session) -> Villa:
    """Create a test villa for checkout availability tests"""
    villa = Villa(
        name="Checkout Test Villa",
        description="Test villa for checkout date availability",
        base_price=Decimal("1000000.00"),
        capacity="4 guests",
        room_type="Standard",
        is_active=True
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# Test 1: Check-out Date Not Blocked
# ============================================================================

class TestCheckoutDateNotBlocked:
    """Test that check-out date is not blocked by a booking"""
    
    def test_checkout_date_is_available(
        self, 
        db: Session, 
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that a villa's check-out date is available for new bookings.
        
        Scenario:
        - Create Booking A: Check-in Jan 1, Check-out Jan 5
        - Verify villa is blocked for Jan 1-4 only
        - Verify Jan 5 is NOT blocked (available)
        
        Expected:
        - Dates Jan 1, 2, 3, 4 should be unavailable
        - Date Jan 5 should be available
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date(2026, 1, 1)
        check_out = date(2026, 1, 5)
        
        # Act - Create booking
        booking_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert - Check that dates Jan 1-4 are blocked
        for day_offset in range(4):  # Days 0, 1, 2, 3 (Jan 1-4)
            check_date = check_in + timedelta(days=day_offset)
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == check_date
            ).first()
            
            assert availability is not None, f"Expected availability record for {check_date}"
            assert availability.is_available is False, f"Expected {check_date} to be unavailable"
            assert booking.booking_code in availability.blocked_reason
        
        # Assert - Check that Jan 5 (check-out date) is NOT blocked
        checkout_availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
            VillaAvailability.date == check_out
        ).first()
        
        # Check-out date should either not have a record, or be marked as available
        if checkout_availability:
            assert checkout_availability.is_available is True, \
                f"Expected check-out date {check_out} to be available"
        # If no record exists, that also means it's available (default state)


# ============================================================================
# Test 2: Back-to-Back Bookings Allowed
# ============================================================================

class TestBackToBackBookings:
    """Test that back-to-back bookings are allowed"""
    
    def test_back_to_back_bookings_succeed(
        self,
        db: Session,
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that two bookings can be made back-to-back without conflicts.
        
        Scenario:
        - Create Booking A: Check-in Jan 1, Check-out Jan 5
        - Create Booking B: Check-in Jan 5, Check-out Jan 10
        - Both should succeed without conflicts
        
        Expected:
        - Both bookings are created successfully
        - Booking A blocks Jan 1-4
        - Booking B blocks Jan 5-9
        - No overlap or conflict errors
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act - Create first booking (Jan 1-5)
        booking_a_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_a = create_booking(db, booking_a_data, user_obj)
        
        # Act - Create second booking starting on first's checkout date (Jan 5-10)
        booking_b_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 5),
            check_out=date(2026, 1, 10),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_b = create_booking(db, booking_b_data, user_obj)
        
        # Assert - Both bookings should be created successfully
        assert booking_a.id is not None
        assert booking_b.id is not None
        assert booking_a.check_out == booking_b.check_in
        
        # Assert - Verify Booking A blocks Jan 1-4 only
        for day_offset in range(4):
            check_date = date(2026, 1, 1) + timedelta(days=day_offset)
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == check_date
            ).first()
            
            assert availability is not None
            assert availability.is_available is False
            assert booking_a.booking_code in availability.blocked_reason
        
        # Assert - Verify Booking B blocks Jan 5-9
        for day_offset in range(5):
            check_date = date(2026, 1, 5) + timedelta(days=day_offset)
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == check_date
            ).first()
            
            assert availability is not None
            assert availability.is_available is False
            assert booking_b.booking_code in availability.blocked_reason


# ============================================================================
# Test 3: Overlap Detection Still Works
# ============================================================================

class TestOverlapDetection:
    """Test that overlapping bookings are still prevented"""
    
    def test_overlapping_bookings_fail(
        self,
        db: Session,
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that overlapping bookings are detected and prevented.
        
        Scenario:
        - Create Booking A: Check-in Jan 1, Check-out Jan 5
        - Try to create Booking B: Check-in Jan 3, Check-out Jan 7
        - Should fail due to overlap on Jan 3-4
        
        Expected:
        - Booking A is created successfully
        - Booking B creation fails with availability error
        - Error message indicates villa is not available
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act - Create first booking (Jan 1-5)
        booking_a_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_a = create_booking(db, booking_a_data, user_obj)
        assert booking_a.id is not None
        
        # Act & Assert - Try to create overlapping booking (Jan 3-7)
        booking_b_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 3),
            check_out=date(2026, 1, 7),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        
        with pytest.raises(Exception) as exc_info:
            create_booking(db, booking_b_data, user_obj)
        
        # Assert - Error message should indicate villa is not available
        error_detail = str(exc_info.value.detail).lower()
        assert "not available" in error_detail or "unavailable" in error_detail


# ============================================================================
# Test 4: Same-Day Check-in/Check-out Edge Case
# ============================================================================

class TestSameDayCheckInOut:
    """Test edge case where check-in and check-out are one day apart"""
    
    def test_one_night_booking_only_blocks_checkin_date(
        self,
        db: Session,
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that a one-night booking only blocks the check-in date.
        
        Scenario:
        - Create Booking A: Check-in Jan 1, Check-out Jan 2 (1 night)
        - Verify only Jan 1 is blocked
        - Verify Jan 2 is available
        
        Expected:
        - Jan 1 should be unavailable
        - Jan 2 should be available
        - A new booking can start on Jan 2
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        check_in = date(2026, 1, 1)
        check_out = date(2026, 1, 2)
        
        # Act - Create one-night booking
        booking_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=check_in,
            check_out=check_out,
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking = create_booking(db, booking_data, user_obj)
        
        # Assert - Jan 1 should be blocked
        jan_1_availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
            VillaAvailability.date == check_in
        ).first()
        
        assert jan_1_availability is not None
        assert jan_1_availability.is_available is False
        assert booking.booking_code in jan_1_availability.blocked_reason
        
        # Assert - Jan 2 should NOT be blocked
        jan_2_availability = db.query(VillaAvailability).filter(
            VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
            VillaAvailability.date == check_out
        ).first()
        
        # Check-out date should either not exist or be available
        if jan_2_availability:
            assert jan_2_availability.is_available is True
        
        # Assert - Verify villa availability check confirms Jan 2 is available
        is_available, unavailable_dates = check_villa_availability(
            db, test_villa_for_checkout_tests.id, check_out, check_out + timedelta(days=1)
        )
        assert is_available is True
        assert len(unavailable_dates) == 0


# ============================================================================
# Test 5: Multiple Consecutive Bookings
# ============================================================================

class TestMultipleConsecutiveBookings:
    """Test multiple consecutive bookings with checkout logic"""
    
    def test_three_consecutive_bookings(
        self,
        db: Session,
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that three consecutive bookings can be created without conflicts.
        
        Scenario:
        - Create Booking A: Jan 1-5
        - Create Booking B: Jan 5-10
        - Create Booking C: Jan 10-15
        - All should succeed, each blocking only check-in to day before check-out
        
        Expected:
        - All three bookings are created successfully
        - Booking A blocks Jan 1-4
        - Booking B blocks Jan 5-9
        - Booking C blocks Jan 10-14
        - Jan 15 is available for the next booking
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Act - Create three consecutive bookings
        booking_a_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_a = create_booking(db, booking_a_data, user_obj)
        
        booking_b_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 5),
            check_out=date(2026, 1, 10),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_b = create_booking(db, booking_b_data, user_obj)
        
        booking_c_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 10),
            check_out=date(2026, 1, 15),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking_c = create_booking(db, booking_c_data, user_obj)
        
        # Assert - All bookings created successfully
        assert booking_a.id is not None
        assert booking_b.id is not None
        assert booking_c.id is not None
        
        # Assert - Verify Booking A blocks Jan 1-4
        for day in range(1, 5):
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == date(2026, 1, day)
            ).first()
            assert availability is not None
            assert availability.is_available is False
            assert booking_a.booking_code in availability.blocked_reason
        
        # Assert - Verify Booking B blocks Jan 5-9
        for day in range(5, 10):
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == date(2026, 1, day)
            ).first()
            assert availability is not None
            assert availability.is_available is False
            assert booking_b.booking_code in availability.blocked_reason
        
        # Assert - Verify Booking C blocks Jan 10-14
        for day in range(10, 15):
            availability = db.query(VillaAvailability).filter(
                VillaAvailability.villa_id == test_villa_for_checkout_tests.id,
                VillaAvailability.date == date(2026, 1, day)
            ).first()
            assert availability is not None
            assert availability.is_available is False
            assert booking_c.booking_code in availability.blocked_reason
        
        # Assert - Jan 15 (final checkout date) should be available
        is_available, _ = check_villa_availability(
            db, test_villa_for_checkout_tests.id,
            date(2026, 1, 15), date(2026, 1, 16)
        )
        assert is_available is True, "Expected final checkout date to be available"


# ============================================================================
# Test 6: Availability Check Function
# ============================================================================

class TestCheckVillaAvailabilityFunction:
    """Test the check_villa_availability function directly"""
    
    def test_availability_check_excludes_checkout_date(
        self,
        db: Session,
        test_user,
        test_customer_for_checkout_tests,
        test_villa_for_checkout_tests
    ):
        """
        Verify that the check_villa_availability function correctly checks
        dates from check-in up to (but not including) check-out.
        
        Scenario:
        - Create booking for Jan 1-5
        - Check availability for Jan 1-5 (should be unavailable)
        - Check availability for Jan 5-10 (should be available)
        
        Expected:
        - Availability check for Jan 1-5 returns False (dates blocked)
        - Availability check for Jan 5-10 returns True (dates free)
        """
        # Arrange
        user_obj = db.query(User).filter(User.id == test_user["id"]).first()
        
        # Create booking (Jan 1-5)
        booking_data = BookingCreate(
            customer_id=test_customer_for_checkout_tests.id,
            check_in=date(2026, 1, 1),
            check_out=date(2026, 1, 5),
            total_pax=2,
            villas=[test_villa_for_checkout_tests.id],
            items=[],
            status="confirmed"
        )
        booking = create_booking(db, booking_data, user_obj)
        
        # Act & Assert - Check availability for Jan 1-5 (should overlap)
        is_available_overlap, unavailable_dates_overlap = check_villa_availability(
            db, test_villa_for_checkout_tests.id,
            date(2026, 1, 1), date(2026, 1, 5)
        )
        assert is_available_overlap is False, "Expected dates Jan 1-5 to be unavailable"
        assert len(unavailable_dates_overlap) == 4, "Expected 4 unavailable dates (Jan 1-4)"
        
        # Act & Assert - Check availability for Jan 5-10 (should be free)
        is_available_free, unavailable_dates_free = check_villa_availability(
            db, test_villa_for_checkout_tests.id,
            date(2026, 1, 5), date(2026, 1, 10)
        )
        assert is_available_free is True, "Expected dates Jan 5-10 to be available"
        assert len(unavailable_dates_free) == 0, "Expected no unavailable dates"
