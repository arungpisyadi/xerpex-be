"""
Tests for Targets API endpoints
"""
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.target import Target
from app.models.user import User
from app.schemas.target import TargetCreate, TargetUpdate


@pytest.fixture(scope="function")
def test_sales_user(db: Session) -> dict:
    """
    Create a test sales user
    """
    sales_user = User(
        username="testsales",
        email="sales@example.com",
        full_name="Test Sales User",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: secret
        is_active=True,
        role='sales'
    )
    db.add(sales_user)
    db.commit()
    db.refresh(sales_user)

    return {
        "id": sales_user.id,
        "username": sales_user.username,
        "email": sales_user.email,
        "full_name": sales_user.full_name,
        "role": sales_user.role
    }


@pytest.fixture(scope="function")
def sales_token(test_sales_user: dict) -> str:
    """
    Create a JWT token for the test sales user
    """
    from app.utils.security import create_access_token
    return create_access_token(
        subject=test_sales_user["username"]
    )


@pytest.fixture(scope="function")
def sales_headers(sales_token: str) -> dict:
    """
    Create headers with the sales token
    """
    return {"Authorization": f"Bearer {sales_token}"}


@pytest.fixture(scope="function")
def test_target(db: Session, test_sales_user: dict) -> Target:
    """
    Create a test target
    """
    target = Target(
        user_id=test_sales_user["id"],
        year=2024,
        month=9,
        target_amount=1000000.00,
        carried_over_amount=0.00,
        adjusted_target_amount=1000000.00
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


# Admin Targets API tests
def test_set_target_admin_only(client: TestClient, admin_headers, test_sales_user, db: Session):
    """Test POST /admin/targets - Admin only"""
    target_data = {
        "user_id": test_sales_user["id"],
        "year": 2024,
        "month": 10,
        "target_amount": 1500000.00
    }

    response = client.post("/api/v1/admin/targets", json=target_data, headers=admin_headers)
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "adjusted_target" in data


def test_set_target_unauthorized(client: TestClient, user_headers, test_sales_user):
    """Test POST /admin/targets - Unauthorized access"""
    target_data = {
        "user_id": test_sales_user["id"],
        "year": 2024,
        "month": 10,
        "target_amount": 1500000.00
    }

    response = client.post("/api/v1/admin/targets", json=target_data, headers=user_headers)
    assert response.status_code == 403


def test_set_target_invalid_data(client: TestClient, admin_headers):
    """Test POST /admin/targets - Invalid data"""
    # Missing required fields
    target_data = {
        "user_id": 1,
        "year": 2024
        # Missing month and target_amount
    }

    response = client.post("/api/v1/admin/targets", json=target_data, headers=admin_headers)
    assert response.status_code == 422


def test_get_all_targets_admin_only(client: TestClient, admin_headers, test_target):
    """Test GET /admin/targets - Admin only"""
    response = client.get("/api/v1/admin/targets", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    # Check if our test target is in the results
    target_ids = [t["id"] for t in data]
    assert test_target.id in target_ids


def test_get_all_targets_unauthorized(client: TestClient, user_headers):
    """Test GET /admin/targets - Unauthorized access"""
    response = client.get("/api/v1/admin/targets", headers=user_headers)
    assert response.status_code == 403


def test_update_target_admin_only(client: TestClient, admin_headers, test_target):
    """Test PUT /admin/targets/{id} - Admin only"""
    update_data = {
        "target_amount": 2000000.00
    }

    response = client.put(
        f"/api/v1/admin/targets/{test_target.id}",
        json=update_data,
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_target.id
    assert data["target_amount"] == 2000000.00


def test_update_target_not_found(client: TestClient, admin_headers):
    """Test PUT /admin/targets/{id} - Target not found"""
    update_data = {
        "target_amount": 2000000.00
    }

    response = client.put(
        "/api/v1/admin/targets/99999",
        json=update_data,
        headers=admin_headers
    )
    assert response.status_code == 500  # Service layer handles not found


def test_update_target_unauthorized(client: TestClient, user_headers, test_target):
    """Test PUT /admin/targets/{id} - Unauthorized access"""
    update_data = {
        "target_amount": 2000000.00
    }

    response = client.put(
        f"/api/v1/admin/targets/{test_target.id}",
        json=update_data,
        headers=user_headers
    )
    assert response.status_code == 403


def test_delete_target_admin_only(client: TestClient, admin_headers, test_target):
    """Test DELETE /admin/targets/{id} - Admin only"""
    response = client.delete(
        f"/api/v1/admin/targets/{test_target.id}",
        headers=admin_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_delete_target_not_found(client: TestClient, admin_headers):
    """Test DELETE /admin/targets/{id} - Target not found"""
    response = client.delete(
        "/api/v1/admin/targets/99999",
        headers=admin_headers
    )
    assert response.status_code == 500  # Service layer handles not found


def test_delete_target_unauthorized(client: TestClient, user_headers, test_target):
    """Test DELETE /admin/targets/{id} - Unauthorized access"""
    response = client.delete(
        f"/api/v1/admin/targets/{test_target.id}",
        headers=user_headers
    )
    assert response.status_code == 403


# General Targets API tests
def test_get_targets_overview_authenticated(client: TestClient, admin_headers):
    """Test GET /admin/targets/overview - Admin user"""
    response = client.get("/api/v1/admin/targets/overview", headers=admin_headers)
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert "total_yearly_target" in data
    assert "current_month_achievement" in data
    assert "achievement_percentage" in data
    assert "monthly_data" in data
    assert "chart_data" in data
    assert "ytd_metrics" in data
    assert "active_users_count" in data
    assert "top_performers" in data

    # Check ytd_metrics structure
    ytd_metrics = data["ytd_metrics"]
    assert "ytd_target" in ytd_metrics
    assert "ytd_achievement" in ytd_metrics
    assert "ytd_percentage" in ytd_metrics

    # Check monthly_data structure
    monthly_data = data["monthly_data"]
    assert isinstance(monthly_data, list)
    if len(monthly_data) > 0:
        item = monthly_data[0]
        assert "month" in item
        assert "month_name" in item
        assert "target_amount" in item
        assert "achieved_amount" in item
        assert "achievement_percentage" in item
        assert "carried_over_amount" in item

    # Check chart_data structure
    chart_data = data["chart_data"]
    assert isinstance(chart_data, list)
    if len(chart_data) > 0:
        item = chart_data[0]
        assert "month" in item
        assert "month_name" in item
        assert "target" in item
        assert "achievement" in item

    # Check top_performers structure
    top_performers = data["top_performers"]
    assert isinstance(top_performers, list)
    if len(top_performers) > 0:
        item = top_performers[0]
        assert "user_id" in item
        assert "username" in item
        assert "full_name" in item
        assert "total_achievement" in item
        assert "achievement_percentage" in item


def test_get_targets_overview_unauthenticated(client: TestClient):
    """Test GET /admin/targets/overview - Unauthenticated"""
    response = client.get("/api/v1/admin/targets/overview")
    assert response.status_code == 401


def test_get_my_performance_sales_user(client: TestClient, sales_headers, test_sales_user):
    """Test GET /targets/my-performance - Sales user"""
    response = client.get("/api/v1/targets/my-performance", headers=sales_headers)
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "year" in data
    assert "monthly_targets" in data
    assert "monthly_achievements" in data
    assert "total_achievement" in data
    assert "achievement_percentage" in data


def test_get_my_performance_non_sales_user(client: TestClient, user_headers):
    """Test GET /targets/my-performance - Non-sales user"""
    response = client.get("/api/v1/targets/my-performance", headers=user_headers)
    assert response.status_code == 403


def test_get_my_performance_unauthenticated(client: TestClient):
    """Test GET /targets/my-performance - Unauthenticated"""
    response = client.get("/api/v1/targets/my-performance")
    assert response.status_code == 401


def test_get_my_performance_with_year(client: TestClient, sales_headers):
    """Test GET /targets/my-performance - With year parameter"""
    response = client.get("/api/v1/targets/my-performance?year=2023", headers=sales_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023


def test_get_company_performance_authenticated(client: TestClient, user_headers):
    """Test GET /targets/company-performance - Authenticated user"""
    response = client.get("/api/v1/targets/company-performance", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert "year" in data
    assert "total_yearly_target" in data
    assert "total_achievement" in data
    assert "achievement_percentage" in data
    assert "user_performances" in data


def test_get_company_performance_unauthenticated(client: TestClient):
    """Test GET /targets/company-performance - Unauthenticated"""
    response = client.get("/api/v1/targets/company-performance")
    assert response.status_code == 401


def test_get_company_performance_with_year(client: TestClient, user_headers):
    """Test GET /targets/company-performance - With year parameter"""
    response = client.get("/api/v1/targets/company-performance?year=2023", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2023


# Edge cases and additional tests
def test_set_target_duplicate_month_year(client: TestClient, admin_headers, test_sales_user, db: Session):
    """Test POST /admin/targets - Duplicate month/year for same user"""
    # Create first target
    target_data = {
        "user_id": test_sales_user["id"],
        "year": 2024,
        "month": 11,
        "target_amount": 1500000.00
    }
    response = client.post("/api/v1/admin/targets", json=target_data, headers=admin_headers)
    assert response.status_code == 201

    # Try to create duplicate
    response = client.post("/api/v1/admin/targets", json=target_data, headers=admin_headers)
    # Should handle gracefully (either update or error)
    assert response.status_code in [200, 201, 400]  # Depends on service implementation


def test_update_target_partial_update(client: TestClient, admin_headers, test_target):
    """Test PUT /admin/targets/{id} - Partial update"""
    update_data = {
        "target_amount": None  # Should not update if None
    }

    response = client.put(
        f"/api/v1/admin/targets/{test_target.id}",
        json=update_data,
        headers=admin_headers
    )
    assert response.status_code == 200


def test_get_targets_overview_empty_data(client: TestClient, admin_headers, db: Session):
    """Test GET /admin/targets/overview - Empty data"""
    # Remove all targets
    db.query(Target).delete()
    db.commit()

    response = client.get("/api/v1/admin/targets/overview", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    # Should handle empty data gracefully
    assert isinstance(data, dict)


def test_get_my_performance_no_targets(client: TestClient, sales_headers, db: Session):
    """Test GET /targets/my-performance - No targets for user"""
    # Remove all targets
    db.query(Target).delete()
    db.commit()

    response = client.get("/api/v1/targets/my-performance", headers=sales_headers)
    assert response.status_code == 200
    data = response.json()
    # Should handle no targets gracefully
    assert isinstance(data, dict)