"""
Test package visibility after removing user isolation
Tests that all users can see packages created by any user
"""
import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.package import Package
from app.models.user import User
from app.utils.security import create_access_token


@pytest.fixture
def user1(db: Session):
    """Create first test user"""
    user = User(
        username="user1",
        email="user1@test.com",
        full_name="User One",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user2(db: Session):
    """Create second test user"""
    user = User(
        username="user2",
        email="user2@test.com",
        full_name="User Two",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True,
        role='user'
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user1_headers(user1: User):
    """Create headers with user1 token"""
    token = create_access_token(subject=user1.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user2_headers(user2: User):
    """Create headers with user2 token"""
    token = create_access_token(subject=user2.username)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_packages(db: Session, user1: User, user2: User):
    """Create test packages for different users"""
    
    # Create packages for user1
    package1 = Package(
        user_id=user1.id,
        name="User1 Package A",
        category="Tours",
        type="Group",
        description="Package created by user1",
        days=3,
        cost_per_pax=500.00,
        min_pax=2
    )
    
    package2 = Package(
        user_id=user1.id,
        name="User1 Package B",
        category="Activities",
        type="Private",
        description="Another package by user1",
        days=1,
        cost_per_pax=150.00,
        min_pax=1
    )
    
    # Create packages for user2
    package3 = Package(
        user_id=user2.id,
        name="User2 Package A",
        category="Tours",
        type="Group",
        description="Package created by user2",
        days=5,
        cost_per_pax=800.00,
        min_pax=4
    )
    
    package4 = Package(
        user_id=user2.id,
        name="User2 Package B",
        category="Transport",
        type="Private",
        description="Another package by user2",
        days=1,
        cost_per_pax=100.00,
        min_pax=1
    )
    
    db.add_all([package1, package2, package3, package4])
    db.commit()
    db.refresh(package1)
    db.refresh(package2)
    db.refresh(package3)
    db.refresh(package4)
    
    return {
        "user1_packages": [package1, package2],
        "user2_packages": [package3, package4],
        "all_packages": [package1, package2, package3, package4]
    }


def test_user1_can_see_all_packages(client, test_packages, user1_headers):
    """Test that user1 can see packages created by user2"""
    
    response = client.get("/api/v1/packages", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    packages = response.json()
    
    # Should see all 4 packages
    assert len(packages) >= 4
    
    # Extract package names
    package_names = [pkg["name"] for pkg in packages]
    
    # Should see packages from both users
    assert "User1 Package A" in package_names
    assert "User1 Package B" in package_names
    assert "User2 Package A" in package_names
    assert "User2 Package B" in package_names


def test_user2_can_see_all_packages(client, test_packages, user2_headers):
    """Test that user2 can see packages created by user1"""
    
    response = client.get("/api/v1/packages", headers=user2_headers)
    
    assert response.status_code == status.HTTP_200_OK
    packages = response.json()
    
    # Should see all 4 packages
    assert len(packages) >= 4
    
    # Extract package names
    package_names = [pkg["name"] for pkg in packages]
    
    # Should see packages from both users
    assert "User1 Package A" in package_names
    assert "User1 Package B" in package_names
    assert "User2 Package A" in package_names
    assert "User2 Package B" in package_names


def test_user1_can_see_user2_package_by_id(client, test_packages, user1: User, user2: User, user1_headers):
    """Test that user1 can retrieve a specific package created by user2"""
    user2_package = test_packages["user2_packages"][0]
    
    response = client.get(f"/api/v1/packages/{user2_package.id}", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    package = response.json()
    
    assert package["id"] == user2_package.id
    assert package["name"] == user2_package.name
    # Successfully retrieved package created by different user


def test_user2_can_see_user1_package_by_id(client, test_packages, user1: User, user2: User, user2_headers):
    """Test that user2 can retrieve a specific package created by user1"""
    user1_package = test_packages["user1_packages"][0]
    
    response = client.get(f"/api/v1/packages/{user1_package.id}", headers=user2_headers)
    
    assert response.status_code == status.HTTP_200_OK
    package = response.json()
    
    assert package["id"] == user1_package.id
    assert package["name"] == user1_package.name
    # Successfully retrieved package created by different user


def test_categories_include_all_users_packages(client, test_packages, user1_headers):
    """Test that categories endpoint returns categories from all users' packages"""
    response = client.get("/api/v1/packages/meta/categories", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    categories = response.json()
    
    # Should include categories from both users
    assert "Tours" in categories
    assert "Activities" in categories
    assert "Transport" in categories


def test_types_include_all_users_packages(client, test_packages, user1_headers):
    """Test that types endpoint returns types from all users' packages"""
    response = client.get("/api/v1/packages/meta/types", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    types = response.json()
    
    # Should include types from both users
    assert "Group" in types
    assert "Private" in types


def test_filter_packages_sees_all_users(client, test_packages, user1_headers):
    """Test that filtering packages shows results from all users"""
    # Filter by category "Tours" which exists in both users' packages
    response = client.get("/api/v1/packages?category=Tours", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    packages = response.json()
    
    # Should find exactly 2 packages with Tours category (one from each user)
    assert len(packages) >= 2
    
    package_names = [pkg["name"] for pkg in packages if pkg["category"] == "Tours"]
    assert "User1 Package A" in package_names
    assert "User2 Package A" in package_names


def test_search_packages_sees_all_users(client, test_packages, user1_headers):
    """Test that searching packages shows results from all users"""
    # Search for "Package A" which exists in both users' packages
    response = client.get("/api/v1/packages?search=Package A", headers=user1_headers)
    
    assert response.status_code == status.HTTP_200_OK
    packages = response.json()
    
    # Should find at least 2 packages (one from each user)
    assert len(packages) >= 2
    
    package_names = [pkg["name"] for pkg in packages]
    assert "User1 Package A" in package_names
    assert "User2 Package A" in package_names


def test_authentication_still_required(client, test_packages):
    """Test that authentication is still required to view packages"""
    # Try to access without authentication
    response = client.get("/api/v1/packages")
    
    # Should require authentication
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_cannot_modify_others_packages(client, test_packages, user1_headers):
    """Test that users still cannot modify packages created by others"""
    # Try to update a package created by user2
    user2_package = test_packages["user2_packages"][0]
    
    update_data = {
        "name": "Modified by User1",
        "cost_per_pax": 999.99
    }
    
    response = client.put(
        f"/api/v1/packages/{user2_package.id}",
        json=update_data,
        headers=user1_headers
    )
    
    # Should not be able to modify another user's package
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_user_cannot_delete_others_packages(client, test_packages, user1_headers):
    """Test that users still cannot delete packages created by others"""
    # Try to delete a package created by user2
    user2_package = test_packages["user2_packages"][0]
    
    response = client.delete(
        f"/api/v1/packages/{user2_package.id}",
        headers=user1_headers
    )
    
    # Should not be able to delete another user's package
    assert response.status_code == status.HTTP_404_NOT_FOUND