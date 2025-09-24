"""
Test phone filtering functionality in user service
"""
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.services.user import (
    get_user_by_phone,
    get_users,
    create_user,
    update_user
)
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User


def test_get_user_by_phone(db: Session):
    """Test getting user by phone number"""
    # Create a test user with phone
    user_data = UserCreate(
        username="phoneuser",
        email="phoneuser@test.com",
        password="testpass123",
        full_name="Phone User",
        role="sales",
        phone="+6281234567890"
    )
    
    created_user = create_user(db, user_data)
    
    # Test finding user by phone (use sanitized format)
    found_user = get_user_by_phone(db, "6281234567890")
    assert found_user is not None
    assert found_user.phone == "6281234567890"
    assert found_user.username == "phoneuser"
    
    # Test with non-existent phone
    not_found = get_user_by_phone(db, "6289999999999")
    assert not_found is None


def test_get_users_with_phone_filter(db: Session):
    """Test filtering users by phone number"""
    # Create test users with different phones
    user1_data = UserCreate(
        username="phoneuser1",
        email="phoneuser1@test.com", 
        password="testpass123",
        full_name="Phone User 1",
        role="sales",
        phone="+6281234567890"
    )
    
    user2_data = UserCreate(
        username="phoneuser2",
        email="phoneuser2@test.com",
        password="testpass123", 
        full_name="Phone User 2",
        role="sales",
        phone="+6287654321098"
    )
    
    user3_data = UserCreate(
        username="phoneuser3",
        email="phoneuser3@test.com",
        password="testpass123",
        full_name="Phone User 3",
        role="sales",
        phone="+6281298765432"  # Contains "812"
    )
    
    create_user(db, user1_data)
    create_user(db, user2_data)
    create_user(db, user3_data)
    
    # Test partial phone matching
    users_with_812 = get_users(db, phone="812")
    phone_numbers = [user.phone for user in users_with_812]
    assert "6281234567890" in phone_numbers
    assert "6281298765432" in phone_numbers
    assert "6287654321098" not in phone_numbers
    
    # Test exact phone matching
    users_exact = get_users(db, phone="6281234567890")
    assert len(users_exact) == 1
    assert users_exact[0].phone == "6281234567890"


def test_create_user_phone_uniqueness(db: Session):
    """Test phone uniqueness validation in create_user"""
    user_data = UserCreate(
        username="phoneuser",
        email="phoneuser@test.com",
        password="testpass123", 
        full_name="Phone User",
        role="sales",
        phone="+6281234567890"
    )
    
    # Create first user
    create_user(db, user_data)
    
    # Try to create second user with same phone
    duplicate_user_data = UserCreate(
        username="phoneuser2", 
        email="phoneuser2@test.com",
        password="testpass123",
        full_name="Phone User 2",
        role="sales", 
        phone="+6281234567890"  # Same phone
    )
    
    with pytest.raises(HTTPException) as exc_info:
        create_user(db, duplicate_user_data)
    
    assert exc_info.value.status_code == 400
    assert "Phone number already registered" in str(exc_info.value.detail)


def test_update_user_phone_uniqueness(db: Session):
    """Test phone uniqueness validation in update_user"""
    # Create two users with different phones
    user1_data = UserCreate(
        username="phoneuser1",
        email="phoneuser1@test.com",
        password="testpass123",
        full_name="Phone User 1", 
        role="sales",
        phone="+6281234567890"
    )
    
    user2_data = UserCreate(
        username="phoneuser2",
        email="phoneuser2@test.com", 
        password="testpass123",
        full_name="Phone User 2",
        role="sales",
        phone="+6287654321098"  
    )
    
    user1 = create_user(db, user1_data)
    user2 = create_user(db, user2_data)
    
    # Try to update user2's phone to user1's phone
    update_data = UserUpdate(phone="+6281234567890")  # user1's phone (will be sanitized)
    
    with pytest.raises(HTTPException) as exc_info:
        update_user(db, user2.id, update_data)
    
    assert exc_info.value.status_code == 400
    assert "Phone number already registered" in str(exc_info.value.detail)
    
    # Test successful phone update
    update_data = UserUpdate(phone="+6289999999999")  # New unique phone
    updated_user = update_user(db, user2.id, update_data)
    assert updated_user.phone == "6289999999999"  # Sanitized format


def test_get_users_combined_filters(db: Session):
    """Test combining phone filter with other filters"""
    # Create users with various combinations
    user_data = UserCreate(
        username="salesuser",
        email="salesuser@test.com",
        password="testpass123",
        full_name="Sales User",
        role="sales", 
        phone="+6281234567890",
        is_active=True
    )
    
    create_user(db, user_data)
    
    # Test combining phone and role filters
    users = get_users(db, role="sales", phone="812", is_active=True)
    assert len(users) >= 1
    assert all(user.role == "sales" for user in users)
    assert all("812" in user.phone for user in users)
    assert all(user.is_active for user in users)