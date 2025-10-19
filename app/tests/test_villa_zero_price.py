"""
Comprehensive tests to verify that villa create and update operations can accept base_price = 0.
Tests both API endpoints and service layer functionality.
"""
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.villa import Villa
from app.models.user import User
from app.schemas.villa import VillaCreate, VillaUpdate
from app.services.villa import create_villa, update_villa, get_villa
from app.utils.security import create_access_token, get_password_hash


@pytest.fixture(scope="function")
def admin_user_with_credentials(db: Session) -> Dict[str, Any]:
    """
    Create a test admin user with the credentials from rules
    """
    admin = User(
        username="admin@tugugroup.co.id",
        email="admin@tugugroup.co.id",
        full_name="Test Admin User",
        password_hash=get_password_hash("1q2w3e4r5t"),
        is_active=True,
        role='admin'
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    return {
        "id": admin.id,
        "username": admin.username,
        "email": admin.email,
        "full_name": admin.full_name,
        "role": admin.role,
        "password": "1q2w3e4r5t"
    }


@pytest.fixture(scope="function")
def admin_credentials_token(admin_user_with_credentials: Dict[str, Any]) -> str:
    """
    Create a JWT token for the admin user with provided credentials
    """
    return create_access_token(
        subject=admin_user_with_credentials["username"]
    )


@pytest.fixture(scope="function")
def admin_credentials_headers(admin_credentials_token: str) -> Dict[str, str]:
    """
    Create headers with the admin credentials token
    """
    return {"Authorization": f"Bearer {admin_credentials_token}"}


# Service Layer Tests for base_price = 0

def test_create_villa_with_zero_price_service(db: Session, admin_user_with_credentials):
    """Test creating a villa with base_price = 0 through the service layer"""
    villa_data = VillaCreate(
        name="Zero Price Villa",
        description="A villa with zero base price for testing",
        capacity=4,
        room_type="deluxe",
        base_price=Decimal("0.00"),
        is_active=True
    )
    
    villa = create_villa(db, villa_data)
    
    # Verify the villa was created successfully
    assert villa.id is not None
    assert villa.name == "Zero Price Villa"
    assert villa.description == "A villa with zero base price for testing"
    assert villa.capacity == 4
    assert villa.room_type == "deluxe"
    assert villa.base_price == Decimal("0.00")
    assert villa.is_active is True
    assert villa.created_at is not None
    assert villa.updated_at is not None


def test_update_villa_to_zero_price_service(db: Session, admin_user_with_credentials):
    """Test updating an existing villa's base_price to 0 through the service layer"""
    # First, create a villa with a non-zero price
    villa_data = VillaCreate(
        name="Update Test Villa",
        description="A villa for testing price updates",
        capacity=6,
        room_type="suite",
        base_price=Decimal("1500000.00"),
        is_active=True
    )
    
    villa = create_villa(db, villa_data)
    assert villa.base_price == Decimal("1500000.00")
    
    # Now update the base_price to 0
    villa_update = VillaUpdate(base_price=Decimal("0.00"))
    updated_villa = update_villa(db, villa.id, villa_update)
    
    # Verify the update was successful
    assert updated_villa.id == villa.id
    assert updated_villa.name == "Update Test Villa"
    assert updated_villa.base_price == Decimal("0.00")
    # Note: updated_at might be the same if update happens very quickly
    assert updated_villa.updated_at >= villa.updated_at


def test_update_villa_from_zero_to_nonzero_price_service(db: Session, admin_user_with_credentials):
    """Test updating a villa from base_price = 0 to a non-zero price through the service layer"""
    # First, create a villa with zero price
    villa_data = VillaCreate(
        name="Zero to Non-Zero Villa",
        description="A villa for testing price updates from zero",
        capacity=2,
        room_type="standard",
        base_price=Decimal("0.00"),
        is_active=True
    )
    
    villa = create_villa(db, villa_data)
    assert villa.base_price == Decimal("0.00")
    
    # Now update the base_price to a non-zero value
    villa_update = VillaUpdate(base_price=Decimal("2000000.00"))
    updated_villa = update_villa(db, villa.id, villa_update)
    
    # Verify the update was successful
    assert updated_villa.id == villa.id
    assert updated_villa.name == "Zero to Non-Zero Villa"
    assert updated_villa.base_price == Decimal("2000000.00")
    # Note: updated_at might be the same if update happens very quickly
    assert updated_villa.updated_at >= villa.updated_at


def test_create_multiple_villas_with_zero_price_service(db: Session, admin_user_with_credentials):
    """Test creating multiple villas with base_price = 0 to ensure no conflicts"""
    villa_names = ["Zero Villa 1", "Zero Villa 2", "Zero Villa 3"]
    created_villas = []
    
    for name in villa_names:
        villa_data = VillaCreate(
            name=name,
            description=f"Description for {name}",
            capacity=4,
            room_type="standard",
            base_price=Decimal("0.00"),
            is_active=True
        )
        
        villa = create_villa(db, villa_data)
        created_villas.append(villa)
        
        # Verify each villa was created successfully
        assert villa.id is not None
        assert villa.name == name
        assert villa.base_price == Decimal("0.00")
    
    # Ensure all villas have unique IDs
    villa_ids = [v.id for v in created_villas]
    assert len(villa_ids) == len(set(villa_ids))


# API Layer Tests for base_price = 0

def test_create_villa_with_zero_price_api(client: TestClient, admin_credentials_headers):
    """Test creating a villa with base_price = 0 through the API"""
    response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "API Zero Price Villa",
            "description": "A villa with zero base price created via API",
            "capacity": 8,
            "room_type": "luxury",
            "base_price": 0.00,
            "is_active": True
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Zero Price Villa"
    assert data["description"] == "A villa with zero base price created via API"
    assert data["capacity"] == 8
    assert data["room_type"] == "luxury"
    assert float(data["base_price"]) == 0.00
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_update_villa_to_zero_price_api(client: TestClient, admin_credentials_headers, db: Session):
    """Test updating an existing villa's base_price to 0 through the API"""
    # First, create a villa through the API
    create_response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "API Update Villa",
            "description": "A villa for API price update testing",
            "capacity": 4,
            "room_type": "deluxe",
            "base_price": 1000000.00,
            "is_active": True
        }
    )
    
    assert create_response.status_code == 201
    villa_data = create_response.json()
    villa_id = villa_data["id"]
    
    # Now update the base_price to 0
    update_response = client.put(
        f"/api/v1/villas/{villa_id}",
        headers=admin_credentials_headers,
        json={
            "base_price": 0.00
        }
    )
    
    assert update_response.status_code == 200
    updated_data = update_response.json()
    assert updated_data["id"] == villa_id
    assert updated_data["name"] == "API Update Villa"
    assert float(updated_data["base_price"]) == 0.00
    assert updated_data["updated_at"] != villa_data["updated_at"]


def test_get_villa_with_zero_price_api(client: TestClient, admin_credentials_headers):
    """Test retrieving a villa with base_price = 0 through the API"""
    # Create a villa with zero price
    create_response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "API Get Zero Villa",
            "description": "A villa with zero price for API retrieval test",
            "capacity": 6,
            "room_type": "suite",
            "base_price": 0.00,
            "is_active": True
        }
    )
    
    assert create_response.status_code == 201
    villa_data = create_response.json()
    villa_id = villa_data["id"]
    
    # Retrieve the villa
    get_response = client.get(f"/api/v1/villas/{villa_id}")
    
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["id"] == villa_id
    assert retrieved_data["name"] == "API Get Zero Villa"
    assert float(retrieved_data["base_price"]) == 0.00


def test_list_villas_includes_zero_price_api(client: TestClient, admin_credentials_headers):
    """Test that villas with base_price = 0 appear in villa listings"""
    # Create a mix of villas with zero and non-zero prices
    villas_to_create = [
        {"name": "Zero Price Villa 1", "base_price": 0.00},
        {"name": "Regular Price Villa", "base_price": 1500000.00},
        {"name": "Zero Price Villa 2", "base_price": 0.00},
    ]
    
    created_villa_ids = []
    
    for villa_data in villas_to_create:
        response = client.post(
            "/api/v1/villas",
            headers=admin_credentials_headers,
            json={
                "name": villa_data["name"],
                "description": f"Description for {villa_data['name']}",
                "capacity": 4,
                "room_type": "standard",
                "base_price": villa_data["base_price"],
                "is_active": True
            }
        )
        assert response.status_code == 201
        created_villa_ids.append(response.json()["id"])
    
    # List all villas
    list_response = client.get("/api/v1/villas")
    assert list_response.status_code == 200
    
    villas_list = list_response.json()
    assert isinstance(villas_list, list)
    
    # Verify that all created villas are in the list
    listed_villa_ids = [v["id"] for v in villas_list]
    for villa_id in created_villa_ids:
        assert villa_id in listed_villa_ids
    
    # Verify that zero-price villas are properly represented
    zero_price_villas = [v for v in villas_list if float(v["base_price"]) == 0.00]
    assert len(zero_price_villas) >= 2  # At least the two we created


# Authentication Tests with Provided Credentials

def test_login_with_provided_credentials(client: TestClient, admin_user_with_credentials):
    """Test login with the credentials provided in the rules"""
    response = client.post(
        "/api/v1/auth/login/json",
        json={
            "email": "admin@tugugroup.co.id",
            "password": "1q2w3e4r5t"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_unauthorized_access_to_villa_creation(client: TestClient):
    """Test that unauthorized users cannot create villas with zero price"""
    response = client.post(
        "/api/v1/villas",
        json={
            "name": "Unauthorized Villa",
            "description": "This should fail",
            "capacity": 4,
            "room_type": "standard",
            "base_price": 0.00,
            "is_active": True
        }
    )
    
    assert response.status_code == 401


def test_regular_user_cannot_create_villa(client: TestClient, user_headers):
    """Test that regular users cannot create villas even with zero price"""
    response = client.post(
        "/api/v1/villas",
        headers=user_headers,
        json={
            "name": "Regular User Villa",
            "description": "This should fail",
            "capacity": 4,
            "room_type": "standard",
            "base_price": 0.00,
            "is_active": True
        }
    )
    
    assert response.status_code == 403


# Integration Tests

def test_end_to_end_villa_lifecycle_with_zero_price(client: TestClient, admin_credentials_headers):
    """Test complete villa lifecycle with zero price: create, read, update, list"""
    # Step 1: Create villa with zero price
    create_response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "Lifecycle Test Villa",
            "description": "Testing complete villa lifecycle",
            "capacity": 6,
            "room_type": "deluxe",
            "base_price": 0.00,
            "is_active": True
        }
    )
    
    assert create_response.status_code == 201
    villa_data = create_response.json()
    villa_id = villa_data["id"]
    assert float(villa_data["base_price"]) == 0.00
    
    # Step 2: Read the villa
    read_response = client.get(f"/api/v1/villas/{villa_id}")
    assert read_response.status_code == 200
    read_data = read_response.json()
    assert read_data["id"] == villa_id
    assert float(read_data["base_price"]) == 0.00
    
    # Step 3: Update to non-zero price
    update_response = client.put(
        f"/api/v1/villas/{villa_id}",
        headers=admin_credentials_headers,
        json={
            "base_price": 1500000.00
        }
    )
    
    assert update_response.status_code == 200
    update_data = update_response.json()
    assert float(update_data["base_price"]) == 1500000.00
    
    # Step 4: Update back to zero price
    revert_response = client.put(
        f"/api/v1/villas/{villa_id}",
        headers=admin_credentials_headers,
        json={
            "base_price": 0.00
        }
    )
    
    assert revert_response.status_code == 200
    revert_data = revert_response.json()
    assert float(revert_data["base_price"]) == 0.00
    
    # Step 5: Verify villa appears in listings with zero price
    list_response = client.get("/api/v1/villas")
    assert list_response.status_code == 200
    
    villas_list = list_response.json()
    target_villa = next((v for v in villas_list if v["id"] == villa_id), None)
    assert target_villa is not None
    assert float(target_villa["base_price"]) == 0.00


def test_villa_zero_price_database_persistence(db: Session, admin_user_with_credentials):
    """Test that zero price is properly persisted in the database"""
    # Create villa through service
    villa_data = VillaCreate(
        name="Persistence Test Villa",
        description="Testing database persistence of zero price",
        capacity=4,
        room_type="standard",
        base_price=Decimal("0.00"),
        is_active=True
    )
    
    villa = create_villa(db, villa_data)
    villa_id = villa.id
    
    # Clear session to force database reload
    db.expunge_all()
    
    # Retrieve villa directly from database
    db_villa = get_villa(db, villa_id)
    
    assert db_villa is not None
    assert db_villa.base_price == Decimal("0.00")
    assert str(db_villa.base_price) == "0.00"
    
    # Query raw database record to double-check
    raw_villa = db.query(Villa).filter(Villa.id == villa_id).first()
    assert raw_villa is not None
    assert raw_villa.base_price == Decimal("0.00")


# Edge Cases and Validation Tests

def test_create_villa_with_negative_price_should_work(client: TestClient, admin_credentials_headers):
    """Test that negative prices are accepted (business rule verification)"""
    response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "Negative Price Villa",
            "description": "Testing negative price acceptance",
            "capacity": 4,
            "room_type": "standard",
            "base_price": -100.00,
            "is_active": True
        }
    )
    
    # Based on schema, negative values should be accepted since no minimum constraint
    assert response.status_code == 201
    data = response.json()
    assert float(data["base_price"]) == -100.00


def test_create_villa_with_large_decimal_places(client: TestClient, admin_credentials_headers):
    """Test that prices with more than 2 decimal places are handled correctly"""
    response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "Decimal Precision Villa",
            "description": "Testing decimal precision handling",
            "capacity": 4,
            "room_type": "standard",
            "base_price": 0.999,  # This should cause validation error due to precision
            "is_active": True
        }
    )
    
    # The pydantic schema should reject values with more than 2 decimal places
    assert response.status_code == 422
    
    # Test with proper decimal precision
    proper_response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "Proper Decimal Villa",
            "description": "Testing proper decimal precision",
            "capacity": 4,
            "room_type": "standard",
            "base_price": 0.99,  # Exactly 2 decimal places
            "is_active": True
        }
    )
    
    assert proper_response.status_code == 201
    data = proper_response.json()
    assert float(data["base_price"]) == 0.99


def test_update_villa_zero_price_with_partial_data(client: TestClient, admin_credentials_headers):
    """Test updating only the base_price field to zero without affecting other fields"""
    # Create villa
    create_response = client.post(
        "/api/v1/villas",
        headers=admin_credentials_headers,
        json={
            "name": "Partial Update Villa",
            "description": "Testing partial updates",
            "capacity": 8,
            "room_type": "luxury",
            "base_price": 2000000.00,
            "is_active": True
        }
    )
    
    assert create_response.status_code == 201
    villa_data = create_response.json()
    villa_id = villa_data["id"]
    original_name = villa_data["name"]
    original_description = villa_data["description"]
    original_capacity = villa_data["capacity"]
    
    # Update only base_price
    update_response = client.put(
        f"/api/v1/villas/{villa_id}",
        headers=admin_credentials_headers,
        json={
            "base_price": 0.00
        }
    )
    
    assert update_response.status_code == 200
    updated_data = update_response.json()
    
    # Verify price was updated but other fields remain unchanged
    assert float(updated_data["base_price"]) == 0.00
    assert updated_data["name"] == original_name
    assert updated_data["description"] == original_description
    assert updated_data["capacity"] == original_capacity