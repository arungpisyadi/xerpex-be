"""
Comprehensive tests for profile update functionality in the XerpeX ERP System
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import get_password_hash


def create_test_admin_user(db: Session) -> tuple[User, str]:
    """
    Helper function to create a test admin user with specific credentials
    
    Args:
        db: Database session
        
    Returns:
        tuple: (User object, plain password)
    """
    password = "1q2w3e4r5t"
    user = User(
        username="admin@tugugroup.co.id",
        email="admin@tugugroup.co.id",
        full_name="Test Admin User",
        password_hash=get_password_hash(password),
        phone="628123456789",
        is_active=True,
        role='admin'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, password


def login_and_get_token(client: TestClient, username: str, password: str) -> str:
    """
    Helper function to login and get authentication token
    
    Args:
        client: TestClient instance
        username: Username or email for login
        password: User password
        
    Returns:
        str: JWT access token
        
    Raises:
        AssertionError: If login fails
    """
    response = client.post(
        "/api/v1/auth/login/json",
        json={
            "email": username,
            "password": password
        }
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    data = response.json()
    assert "access_token" in data, "No access token in response"
    return data["access_token"]


class TestUpdatePersonalInfo:
    """Test cases for personal information updates"""
    
    def test_update_personal_info_success(self, client: TestClient, db: Session):
        """
        Test successful personal info update
        
        This test verifies that a user can successfully update their full_name,
        email, and phone number when all fields are provided.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update personal info
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={
                "full_name": "Updated Full Name",
                "email": "updated@tugugroup.co.id",
                "phone": "628987654321"
            }
        )
        
        # Verify response
        assert response.status_code == 200, f"Update failed: {response.json()}"
        data = response.json()
        assert data["full_name"] == "Updated Full Name", "Full name not updated"
        assert data["email"] == "updated@tugugroup.co.id", "Email not updated"
        assert data["phone"] == "628987654321", "Phone not updated"
        assert data["id"] == user.id, "User ID mismatch"
    
    def test_update_personal_info_partial(self, client: TestClient, db: Session):
        """
        Test partial update (only full_name)
        
        This test verifies that a user can update only their full_name
        without affecting other fields like email or phone.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        original_email = user.email
        original_phone = user.phone
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update only full_name
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={
                "full_name": "Only Name Changed"
            }
        )
        
        # Verify response
        assert response.status_code == 200, f"Update failed: {response.json()}"
        data = response.json()
        assert data["full_name"] == "Only Name Changed", "Full name not updated"
        assert data["email"] == original_email, "Email should not change"
        assert data["phone"] == original_phone, "Phone should not change"
    
    def test_update_personal_info_email_already_exists(self, client: TestClient, db: Session):
        """
        Test email uniqueness validation
        
        This test verifies that a user cannot update their email to one
        that is already registered by another user.
        """
        # Create two test users
        user1, password1 = create_test_admin_user(db)
        
        # Create second user with different email
        password2 = "password123"
        user2 = User(
            username="user2@tugugroup.co.id",
            email="user2@tugugroup.co.id",
            full_name="User Two",
            password_hash=get_password_hash(password2),
            is_active=True,
            role='user'
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)
        
        # Login as user2 and try to update email to user1's email
        token = login_and_get_token(client, user2.username, password2)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={
                "email": user1.email  # Try to use existing email
            }
        )
        
        # Verify error response
        assert response.status_code == 400, "Should return 400 for duplicate email"
        data = response.json()
        assert "already registered" in data["detail"].lower(), "Error message should mention duplicate email"
    
    def test_update_personal_info_no_fields(self, client: TestClient, db: Session):
        """
        Test validation when no fields are provided
        
        This test verifies that the API returns a 422 validation error
        when attempting to update personal info without providing any fields.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to update with empty data
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={}
        )
        
        # Verify validation error
        assert response.status_code == 422, "Should return 422 validation error"
        data = response.json()
        assert "detail" in data, "Response should contain error details"
    
    def test_update_personal_info_unauthorized(self, client: TestClient, db: Session):
        """
        Test authentication requirement
        
        This test verifies that updating personal info without an
        authentication token results in a 401 Unauthorized error.
        """
        # Try to update without token
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            json={
                "full_name": "Unauthorized Update"
            }
        )
        
        # Verify unauthorized response
        assert response.status_code == 401, "Should return 401 for unauthorized access"


class TestUpdatePassword:
    """Test cases for password updates"""
    
    def test_update_password_success(self, client: TestClient, db: Session):
        """
        Test successful password update
        
        This test verifies that a user can successfully update their password
        when providing the correct current password and a valid new password.
        It also verifies that the user can login with the new password.
        """
        # Create test user and login
        user, old_password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, old_password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update password
        new_password = "newpassword123"
        response = client.put(
            "/api/v1/auth/profile/password",
            headers=headers,
            json={
                "current_password": old_password,
                "new_password": new_password
            }
        )
        
        # Verify success response
        assert response.status_code == 200, f"Password update failed: {response.json()}"
        data = response.json()
        assert "message" in data, "Response should contain success message"
        assert "success" in data["message"].lower(), "Message should indicate success"
        
        # Verify can login with new password
        new_token = login_and_get_token(client, user.username, new_password)
        assert new_token is not None, "Should be able to login with new password"
        assert len(new_token) > 0, "New token should not be empty"
        
        # Verify cannot login with old password
        response = client.post(
            "/api/v1/auth/login/json",
            json={
                "email": user.username,
                "password": old_password
            }
        )
        assert response.status_code == 401, "Should not be able to login with old password"
    
    def test_update_password_wrong_current_password(self, client: TestClient, db: Session):
        """
        Test current password validation
        
        This test verifies that attempting to update password with an
        incorrect current password results in a 401 Unauthorized error.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to update with wrong current password
        response = client.put(
            "/api/v1/auth/profile/password",
            headers=headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword123"
            }
        )
        
        # Verify error response
        assert response.status_code == 401, "Should return 401 for incorrect current password"
        data = response.json()
        assert "incorrect" in data["detail"].lower(), "Error message should mention incorrect password"
    
    def test_update_password_same_as_current(self, client: TestClient, db: Session):
        """
        Test new password validation (must be different from current)
        
        This test verifies that attempting to set a new password that is
        the same as the current password results in a 422 validation error.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to update with same password
        response = client.put(
            "/api/v1/auth/profile/password",
            headers=headers,
            json={
                "current_password": password,
                "new_password": password  # Same as current
            }
        )
        
        # Verify validation error
        assert response.status_code == 422, "Should return 422 validation error"
        data = response.json()
        assert "detail" in data, "Response should contain error details"
    
    def test_update_password_too_short(self, client: TestClient, db: Session):
        """
        Test password length validation
        
        This test verifies that attempting to set a new password shorter
        than 8 characters results in a 422 validation error.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to update with short password
        response = client.put(
            "/api/v1/auth/profile/password",
            headers=headers,
            json={
                "current_password": password,
                "new_password": "short1"  # Only 6 characters
            }
        )
        
        # Verify validation error
        assert response.status_code == 422, "Should return 422 validation error for short password"
        data = response.json()
        assert "detail" in data, "Response should contain error details"
    
    def test_update_password_unauthorized(self, client: TestClient, db: Session):
        """
        Test authentication requirement
        
        This test verifies that attempting to update password without an
        authentication token results in a 401 Unauthorized error.
        """
        # Try to update without token
        response = client.put(
            "/api/v1/auth/profile/password",
            json={
                "current_password": "somepassword",
                "new_password": "newpassword123"
            }
        )
        
        # Verify unauthorized response
        assert response.status_code == 401, "Should return 401 for unauthorized access"


class TestProfileUpdatesEdgeCases:
    """Additional edge case tests for profile updates"""
    
    def test_update_personal_info_phone_already_exists(self, client: TestClient, db: Session):
        """
        Test phone uniqueness validation
        
        This test verifies that a user cannot update their phone to one
        that is already registered by another user.
        """
        # Create two test users
        user1, password1 = create_test_admin_user(db)
        
        # Create second user with different phone
        password2 = "password123"
        user2 = User(
            username="user2@tugugroup.co.id",
            email="user2@tugugroup.co.id",
            full_name="User Two",
            phone="628111111111",
            password_hash=get_password_hash(password2),
            is_active=True,
            role='user'
        )
        db.add(user2)
        db.commit()
        db.refresh(user2)
        
        # Login as user2 and try to update phone to user1's phone
        token = login_and_get_token(client, user2.username, password2)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={
                "phone": user1.phone  # Try to use existing phone
            }
        )
        
        # Verify error response
        assert response.status_code == 400, "Should return 400 for duplicate phone"
        data = response.json()
        assert "already registered" in data["detail"].lower(), "Error message should mention duplicate phone"
    
    def test_update_personal_info_multiple_fields(self, client: TestClient, db: Session):
        """
        Test updating multiple fields at once
        
        This test verifies that all provided fields are updated correctly
        when multiple fields are updated in a single request.
        """
        # Create test user and login
        user, password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update multiple fields
        response = client.put(
            "/api/v1/auth/profile/personal-info",
            headers=headers,
            json={
                "full_name": "Multi Update",
                "email": "multi@tugugroup.co.id",
                "phone": "628999999999"
            }
        )
        
        # Verify all fields are updated
        assert response.status_code == 200, f"Update failed: {response.json()}"
        data = response.json()
        assert data["full_name"] == "Multi Update", "Full name not updated"
        assert data["email"] == "multi@tugugroup.co.id", "Email not updated"
        assert data["phone"] == "628999999999", "Phone not updated"
    
    def test_update_password_with_special_characters(self, client: TestClient, db: Session):
        """
        Test password update with special characters
        
        This test verifies that passwords containing special characters
        are handled correctly.
        """
        # Create test user and login
        user, old_password = create_test_admin_user(db)
        token = login_and_get_token(client, user.username, old_password)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Update to password with special characters
        new_password = "P@ssw0rd!#$%"
        response = client.put(
            "/api/v1/auth/profile/password",
            headers=headers,
            json={
                "current_password": old_password,
                "new_password": new_password
            }
        )
        
        # Verify success
        assert response.status_code == 200, f"Password update failed: {response.json()}"
        
        # Verify can login with new password
        new_token = login_and_get_token(client, user.username, new_password)
        assert new_token is not None, "Should be able to login with new password containing special characters"