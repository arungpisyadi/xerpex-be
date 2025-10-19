"""
Unit tests for villa capacity field as string

Tests verify that the capacity field works correctly as a string type
in both the database model and API validation.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.villa import Villa
from app.schemas.villa import VillaCreate, VillaUpdate, Villa as VillaSchema
from app.services.villa import create_villa, update_villa, get_villa, get_villas


class TestVillaCapacityString:
    """Test villa capacity field as string"""

    def test_create_villa_with_string_capacity(self, db: Session):
        """Test creating a villa with string capacity"""
        villa_data = VillaCreate(
            name="Test Villa",
            description="A test villa",
            capacity="10",  # String capacity
            room_type="Deluxe",
            base_price=Decimal("100.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.id is not None
        assert villa.name == "Test Villa"
        assert villa.capacity == "10"  # Should be stored as string
        assert isinstance(villa.capacity, str)
        assert villa.room_type == "Deluxe"
        assert villa.is_active is True

    def test_create_villa_with_numeric_string_capacity(self, db: Session):
        """Test creating a villa with numeric string capacity"""
        villa_data = VillaCreate(
            name="Numeric String Villa",
            description="Villa with numeric string capacity",
            capacity="25",
            room_type="Suite",
            base_price=Decimal("150.50"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == "25"
        assert isinstance(villa.capacity, str)

    def test_create_villa_with_complex_string_capacity(self, db: Session):
        """Test creating a villa with complex string capacity (e.g., '2-4 persons')"""
        villa_data = VillaCreate(
            name="Complex Capacity Villa",
            description="Villa with complex capacity string",
            capacity="2-4 persons",
            room_type="Standard",
            base_price=Decimal("80.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == "2-4 persons"
        assert isinstance(villa.capacity, str)

    def test_update_villa_capacity_to_string(self, db: Session):
        """Test updating villa capacity to a different string"""
        # Create initial villa
        villa_data = VillaCreate(
            name="Update Test Villa",
            description="Test villa for update",
            capacity="5",
            room_type="Standard",
            base_price=Decimal("100.00"),
            is_active=True
        )
        villa = create_villa(db, villa_data)
        
        # Update capacity
        update_data = VillaUpdate(capacity="10-12 persons")
        updated_villa = update_villa(db, villa.id, update_data)
        
        assert updated_villa.capacity == "10-12 persons"
        assert isinstance(updated_villa.capacity, str)

    def test_get_villa_returns_string_capacity(self, db: Session):
        """Test that getting a villa returns capacity as string"""
        villa_data = VillaCreate(
            name="Get Test Villa",
            description="Test villa for get",
            capacity="8",
            room_type="Deluxe",
            base_price=Decimal("120.00"),
            is_active=True
        )
        created_villa = create_villa(db, villa_data)
        
        retrieved_villa = get_villa(db, created_villa.id)
        
        assert retrieved_villa is not None
        assert retrieved_villa.capacity == "8"
        assert isinstance(retrieved_villa.capacity, str)

    def test_villa_schema_validation_accepts_string_capacity(self):
        """Test that VillaCreate schema accepts string capacity"""
        villa_data = {
            "name": "Schema Test Villa",
            "description": "Test villa for schema",
            "capacity": "15",
            "room_type": "Premium",
            "base_price": Decimal("200.00"),
            "is_active": True
        }
        
        villa = VillaCreate(**villa_data)
        
        assert villa.capacity == "15"
        assert isinstance(villa.capacity, str)

    def test_villa_schema_validation_accepts_complex_string_capacity(self):
        """Test that VillaCreate schema accepts complex string capacity"""
        villa_data = {
            "name": "Complex Schema Villa",
            "description": "Test villa with complex capacity",
            "capacity": "4-6 guests",
            "room_type": "Family",
            "base_price": Decimal("250.00"),
            "is_active": True
        }
        
        villa = VillaCreate(**villa_data)
        
        assert villa.capacity == "4-6 guests"

    def test_villa_update_schema_accepts_string_capacity(self):
        """Test that VillaUpdate schema accepts string capacity"""
        update_data = {
            "capacity": "20-25 persons"
        }
        
        villa_update = VillaUpdate(**update_data)
        
        assert villa_update.capacity == "20-25 persons"

    def test_villa_response_schema_includes_string_capacity(self, db: Session):
        """Test that Villa response schema includes capacity as string"""
        villa_data = VillaCreate(
            name="Response Schema Villa",
            description="Test villa for response schema",
            capacity="12",
            room_type="Deluxe",
            base_price=Decimal("180.00"),
            is_active=True
        )
        created_villa = create_villa(db, villa_data)
        
        # Convert to schema
        villa_schema = VillaSchema.model_validate(created_villa)
        
        assert villa_schema.capacity == "12"
        assert isinstance(villa_schema.capacity, str)

    def test_get_villas_with_string_capacity(self, db: Session):
        """Test getting multiple villas with string capacity"""
        # Create multiple villas
        for i in range(3):
            villa_data = VillaCreate(
                name=f"Villa {i}",
                description=f"Test villa {i}",
                capacity=f"{5 + i * 5}",
                room_type="Standard",
                base_price=Decimal("100.00"),
                is_active=True
            )
            create_villa(db, villa_data)
        
        villas = get_villas(db, limit=10)
        
        assert len(villas) >= 3
        for villa in villas:
            assert isinstance(villa.capacity, str)

    def test_villa_capacity_empty_string(self, db: Session):
        """Test creating a villa with empty string capacity"""
        villa_data = VillaCreate(
            name="Empty Capacity Villa",
            description="Test villa with empty capacity",
            capacity="",
            room_type="Standard",
            base_price=Decimal("100.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == ""
        assert isinstance(villa.capacity, str)

    def test_villa_capacity_with_special_characters(self, db: Session):
        """Test creating a villa with special characters in capacity"""
        villa_data = VillaCreate(
            name="Special Chars Villa",
            description="Test villa with special chars in capacity",
            capacity="4-6 (max 8)",
            room_type="Standard",
            base_price=Decimal("100.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == "4-6 (max 8)"
        assert isinstance(villa.capacity, str)

    def test_villa_capacity_with_unicode(self, db: Session):
        """Test creating a villa with unicode characters in capacity"""
        villa_data = VillaCreate(
            name="Unicode Villa",
            description="Test villa with unicode in capacity",
            capacity="4-6 人",
            room_type="Standard",
            base_price=Decimal("100.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == "4-6 人"
        assert isinstance(villa.capacity, str)

    def test_villa_capacity_long_string(self, db: Session):
        """Test creating a villa with long string capacity"""
        long_capacity = "Suitable for 4-6 guests, can accommodate up to 8 with additional beds"
        villa_data = VillaCreate(
            name="Long Capacity Villa",
            description="Test villa with long capacity string",
            capacity=long_capacity,
            room_type="Standard",
            base_price=Decimal("100.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        
        assert villa.capacity == long_capacity
        assert isinstance(villa.capacity, str)
