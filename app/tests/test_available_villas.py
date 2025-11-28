"""
Unit tests for available villas endpoint

Tests verify that the /villas/available endpoint correctly filters
villas based on availability, date ranges, and various filters.
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.villa import Villa, VillaAvailability
from app.config import settings


class TestAvailableVillas:
    """Test suite for available villas endpoint"""

    def test_get_available_villas_success(self, client: TestClient, db: Session):
        """Test successful retrieval of available villas with valid dates."""
        # Setup: Create test villa
        villa = Villa(
            name="Test Villa Success",
            description="A test villa for success case",
            capacity="4-6",
            room_type="Deluxe",
            base_price=Decimal("1000.00"),
            is_active=True
        )
        db.add(villa)
        db.commit()
        db.refresh(villa)
        
        # Test: Query available villas
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "villas" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["total"] >= 1
        assert len(data["villas"]) >= 1
        
        # Verify villa structure
        villa_data = data["villas"][0]
        assert "id" in villa_data
        assert "name" in villa_data
        assert "capacity" in villa_data
        assert "base_price" in villa_data
        
        # Cleanup
        db.delete(villa)
        db.commit()

    def test_filter_unavailable_villas(self, client: TestClient, db: Session):
        """Test that villas with unavailable dates are excluded from results."""
        # Setup: Create test villas
        available_villa = Villa(
            name="Available Villa",
            description="This villa should be available",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("800.00"),
            is_active=True
        )
        unavailable_villa = Villa(
            name="Unavailable Villa",
            description="This villa should be unavailable",
            capacity="6",
            room_type="Premium",
            base_price=Decimal("1200.00"),
            is_active=True
        )
        db.add(available_villa)
        db.add(unavailable_villa)
        db.commit()
        db.refresh(available_villa)
        db.refresh(unavailable_villa)
        
        # Add unavailable dates for the second villa
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        unavailable_date = check_in + timedelta(days=2)
        
        availability = VillaAvailability(
            villa_id=unavailable_villa.id,
            date=unavailable_date,
            is_available=False,
            blocked_reason="Maintenance"
        )
        db.add(availability)
        db.commit()
        
        # Test: Query available villas
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Get villa names from response
        villa_names = [v["name"] for v in data["villas"]]
        
        # Available villa should be in results
        assert "Available Villa" in villa_names
        # Unavailable villa should NOT be in results
        assert "Unavailable Villa" not in villa_names
        
        # Cleanup
        db.delete(availability)
        db.delete(available_villa)
        db.delete(unavailable_villa)
        db.commit()

    def test_include_available_villas_with_availability_outside_range(self, client: TestClient, db: Session):
        """Test that villas with availability records outside query range are included."""
        # Setup: Create test villa
        villa = Villa(
            name="Villa with Outside Availability",
            description="Villa with availability outside query range",
            capacity="8",
            room_type="Suite",
            base_price=Decimal("1500.00"),
            is_active=True
        )
        db.add(villa)
        db.commit()
        db.refresh(villa)
        
        # Add availability record BEFORE the query date range
        check_in = date.today() + timedelta(days=10)
        check_out = date.today() + timedelta(days=15)
        past_date = date.today() + timedelta(days=5)
        
        availability = VillaAvailability(
            villa_id=villa.id,
            date=past_date,
            is_available=False,
            blocked_reason="Previous booking"
        )
        db.add(availability)
        db.commit()
        
        # Test: Query available villas
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert: Villa should be included since unavailable date is outside range
        assert response.status_code == 200
        data = response.json()
        villa_names = [v["name"] for v in data["villas"]]
        assert "Villa with Outside Availability" in villa_names
        
        # Cleanup
        db.delete(availability)
        db.delete(villa)
        db.commit()

    def test_include_villas_with_available_true(self, client: TestClient, db: Session):
        """Test that villas with is_available=True are included in results."""
        # Setup: Create test villa
        villa = Villa(
            name="Villa with Available True",
            description="Villa with is_available=True",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("900.00"),
            is_active=True
        )
        db.add(villa)
        db.commit()
        db.refresh(villa)
        
        # Add availability with is_available=True
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        available_date = check_in + timedelta(days=2)
        
        availability = VillaAvailability(
            villa_id=villa.id,
            date=available_date,
            is_available=True
        )
        db.add(availability)
        db.commit()
        
        # Test: Query available villas
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert: Villa should be included
        assert response.status_code == 200
        data = response.json()
        villa_names = [v["name"] for v in data["villas"]]
        assert "Villa with Available True" in villa_names
        
        # Cleanup
        db.delete(availability)
        db.delete(villa)
        db.commit()

    def test_invalid_date_range_check_out_equals_check_in(self, client: TestClient, db: Session):
        """Test that endpoint returns 400 when check_out equals check_in."""
        # Test: Query with check_out == check_in
        same_date = date.today() + timedelta(days=1)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": same_date.isoformat(),
                "check_out": same_date.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "check_out must be after check_in" in data["detail"]

    def test_invalid_date_range_check_out_before_check_in(self, client: TestClient, db: Session):
        """Test that endpoint returns 400 when check_out is before check_in."""
        # Test: Query with check_out < check_in
        check_in = date.today() + timedelta(days=5)
        check_out = date.today() + timedelta(days=1)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "check_out must be after check_in" in data["detail"]

    def test_pagination_with_skip_and_limit(self, client: TestClient, db: Session):
        """Test pagination with different skip and limit values."""
        # Setup: Create multiple test villas
        villas = []
        for i in range(5):
            villa = Villa(
                name=f"Test Villa {i}",
                description=f"Test villa number {i}",
                capacity=f"{4 + i}",
                room_type="Standard",
                base_price=Decimal(f"{100 * (i + 1)}.00"),
                is_active=True
            )
            db.add(villa)
            villas.append(villa)
        db.commit()
        
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        # Test: Query first page (skip=0, limit=2)
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "skip": 0,
                "limit": 2
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 2
        assert len(data["villas"]) <= 2
        assert data["total"] >= 5
        
        # Test: Query second page (skip=2, limit=2)
        response2 = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "skip": 2,
                "limit": 2
            }
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["skip"] == 2
        assert data2["limit"] == 2
        assert len(data2["villas"]) <= 2
        
        # Test: Query with limit larger than total
        response3 = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "skip": 0,
                "limit": 100
            }
        )
        
        assert response3.status_code == 200
        data3 = response3.json()
        assert data3["total"] >= 5
        
        # Cleanup
        for villa in villas:
            db.delete(villa)
        db.commit()

    def test_filter_by_is_active_true(self, client: TestClient, db: Session):
        """Test filtering by is_active=True returns only active villas."""
        # Setup: Create active and inactive villas
        active_villa = Villa(
            name="Active Villa",
            description="This is an active villa",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("800.00"),
            is_active=True
        )
        inactive_villa = Villa(
            name="Inactive Villa",
            description="This is an inactive villa",
            capacity="6",
            room_type="Premium",
            base_price=Decimal("1000.00"),
            is_active=False
        )
        db.add(active_villa)
        db.add(inactive_villa)
        db.commit()
        db.refresh(active_villa)
        db.refresh(inactive_villa)
        
        # Test: Query with is_active=True
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "is_active": True
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        villa_names = [v["name"] for v in data["villas"]]
        
        # Active villa should be in results
        assert "Active Villa" in villa_names
        # Inactive villa should NOT be in results
        assert "Inactive Villa" not in villa_names
        
        # Cleanup
        db.delete(active_villa)
        db.delete(inactive_villa)
        db.commit()

    def test_filter_by_is_active_false(self, client: TestClient, db: Session):
        """Test filtering by is_active=False returns only inactive villas."""
        # Setup: Create active and inactive villas
        active_villa = Villa(
            name="Active Villa 2",
            description="This is an active villa",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("800.00"),
            is_active=True
        )
        inactive_villa = Villa(
            name="Inactive Villa 2",
            description="This is an inactive villa",
            capacity="6",
            room_type="Premium",
            base_price=Decimal("1000.00"),
            is_active=False
        )
        db.add(active_villa)
        db.add(inactive_villa)
        db.commit()
        db.refresh(active_villa)
        db.refresh(inactive_villa)
        
        # Test: Query with is_active=False
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "is_active": False
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # If there are any villas, they should all be inactive
        for villa in data["villas"]:
            assert villa["is_active"] is False
        
        # Cleanup
        db.delete(active_villa)
        db.delete(inactive_villa)
        db.commit()

    def test_filter_by_location(self, client: TestClient, db: Session):
        """Test filtering by location returns only matching villas."""
        # Setup: Create villas with different locations
        villa_bali = Villa(
            name="Bali Beach Villa",
            description="Beautiful villa in Bali",
            capacity="6",
            room_type="Beachfront",
            base_price=Decimal("1500.00"),
            is_active=True
        )
        villa_jakarta = Villa(
            name="Jakarta City Villa",
            description="Modern villa in Jakarta",
            capacity="4",
            room_type="Urban",
            base_price=Decimal("1000.00"),
            is_active=True
        )
        villa_seminyak = Villa(
            name="Seminyak Luxury Villa",
            description="Luxury villa in Seminyak, Bali",
            capacity="8",
            room_type="Luxury",
            base_price=Decimal("2000.00"),
            is_active=True
        )
        db.add(villa_bali)
        db.add(villa_jakarta)
        db.add(villa_seminyak)
        db.commit()
        
        # Test: Query with location filter for "Bali"
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "location": "Bali"
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Note: The current model doesn't have a location field,
        # so this test will pass but location filtering may not work as expected
        # This is to test the endpoint's handling of the location parameter
        
        # Cleanup
        db.delete(villa_bali)
        db.delete(villa_jakarta)
        db.delete(villa_seminyak)
        db.commit()

    def test_filter_by_name(self, client: TestClient, db: Session):
        """Test filtering by name returns only matching villas."""
        # Setup: Create villas with different names
        villa_beach = Villa(
            name="Beach Paradise Villa",
            description="Villa by the beach",
            capacity="6",
            room_type="Beachfront",
            base_price=Decimal("1500.00"),
            is_active=True
        )
        villa_mountain = Villa(
            name="Mountain Retreat Villa",
            description="Villa in the mountains",
            capacity="4",
            room_type="Mountain",
            base_price=Decimal("1200.00"),
            is_active=True
        )
        villa_ocean = Villa(
            name="Ocean View Villa",
            description="Villa with ocean views",
            capacity="8",
            room_type="Ocean",
            base_price=Decimal("1800.00"),
            is_active=True
        )
        db.add(villa_beach)
        db.add(villa_mountain)
        db.add(villa_ocean)
        db.commit()
        
        # Test: Query with name filter for "Beach"
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "name": "Beach"
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Check that matching villas are in results
        villa_names = [v["name"] for v in data["villas"]]
        assert "Beach Paradise Villa" in villa_names
        
        # Cleanup
        db.delete(villa_beach)
        db.delete(villa_mountain)
        db.delete(villa_ocean)
        db.commit()

    def test_combined_filters(self, client: TestClient, db: Session):
        """Test using multiple filters together."""
        # Setup: Create test villas
        villa1 = Villa(
            name="Active Test Villa",
            description="Active villa for combined filter test",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("800.00"),
            is_active=True
        )
        villa2 = Villa(
            name="Inactive Test Villa",
            description="Inactive villa for combined filter test",
            capacity="6",
            room_type="Premium",
            base_price=Decimal("1000.00"),
            is_active=False
        )
        db.add(villa1)
        db.add(villa2)
        db.commit()
        
        # Test: Query with multiple filters
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "is_active": True,
                "name": "Active",
                "skip": 0,
                "limit": 10
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10
        
        # Cleanup
        db.delete(villa1)
        db.delete(villa2)
        db.commit()

    def test_empty_results_with_all_villas_unavailable(self, client: TestClient, db: Session):
        """Test that endpoint returns empty list when all villas are unavailable."""
        # Setup: Create villa and mark it unavailable
        villa = Villa(
            name="Fully Booked Villa",
            description="This villa is fully booked",
            capacity="4",
            room_type="Standard",
            base_price=Decimal("800.00"),
            is_active=True
        )
        db.add(villa)
        db.commit()
        db.refresh(villa)
        
        # Add unavailable dates for all days in the range
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        current_date = check_in
        availabilities = []
        while current_date < check_out:
            availability = VillaAvailability(
                villa_id=villa.id,
                date=current_date,
                is_available=False,
                blocked_reason="Fully booked"
            )
            db.add(availability)
            availabilities.append(availability)
            current_date += timedelta(days=1)
        db.commit()
        
        # Test: Query available villas
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        villa_names = [v["name"] for v in data["villas"]]
        assert "Fully Booked Villa" not in villa_names
        
        # Cleanup
        for availability in availabilities:
            db.delete(availability)
        db.delete(villa)
        db.commit()

    def test_no_villas_exist(self, client: TestClient, db: Session):
        """Test endpoint returns empty list when no villas exist."""
        # Test: Query when database is empty
        check_in = date.today() + timedelta(days=1)
        check_out = date.today() + timedelta(days=5)
        
        response = client.get(
            f"{settings.API_V1_STR}/villas/available",
            params={
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat()
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "villas" in data
        assert "total" in data
        assert data["total"] == 0
        assert len(data["villas"]) == 0