"""
Tests for API endpoints
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.tests.utils import (
    create_test_villa, create_test_booking, create_test_payment,
    create_test_invoice, create_complete_test_booking
)


# Auth API tests
def test_login(client: TestClient, test_user):
    """Test login endpoint"""
    # Test successful login
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": test_user["username"],
            "password": "secret"  # Password from conftest.py
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Test failed login - wrong password
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": test_user["username"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    
    # Test failed login - user doesn't exist
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "nonexistentuser",
            "password": "password"
        }
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient, user_headers):
    """Test get current user endpoint"""
    response = client.get("/api/v1/auth/me", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert "email" in data
    assert "is_active" in data


def test_register_user(client: TestClient):
    """Test register user endpoint"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "new@example.com",
            "full_name": "New User",
            "password": "password123"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data


# User API tests
def test_get_users(client: TestClient, admin_headers, user_headers):
    """Test get users endpoint"""
    # Test as admin
    response = client.get("/api/v1/users/", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Test as regular user (should be forbidden)
    response = client.get("/api/v1/users/", headers=user_headers)
    assert response.status_code == 403


def test_get_sales_users(client: TestClient, user_headers, admin_headers, db: Session):
    """Test get sales users endpoint"""
    # Create test sales users
    from app.models.user import User
    from app.utils.security import get_password_hash
    
    # Create active sales user
    active_sales_user = User(
        username="sales1",
        email="sales1@example.com",
        full_name="Active Sales User",
        password_hash=get_password_hash("password"),
        role="sales",
        is_active=True
    )
    db.add(active_sales_user)
    
    # Create inactive sales user (should not appear in results)
    inactive_sales_user = User(
        username="sales2",
        email="sales2@example.com",
        full_name="Inactive Sales User",
        password_hash=get_password_hash("password"),
        role="sales",
        is_active=False
    )
    db.add(inactive_sales_user)
    
    # Create active non-sales user (should not appear in results)
    admin_user = User(
        username="admin1",
        email="admin1@example.com",
        full_name="Admin User",
        password_hash=get_password_hash("password"),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    
    db.commit()
    
    # Test as regular user - should work since any authenticated user can access
    response = client.get("/api/v1/users/sales", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Should only contain the active sales user
    assert len(data) == 1
    assert data[0]["id"] == active_sales_user.id
    assert data[0]["full_name"] == "Active Sales User"
    
    # Verify response only contains id and full_name (SalesUserResponse schema)
    for user in data:
        assert "id" in user
        assert "full_name" in user
        assert len(user.keys()) == 2  # Should only have these two fields
    
    # Test as admin - should also work
    response = client.get("/api/v1/users/sales", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == active_sales_user.id


def test_get_sales_users_unauthorized(client: TestClient):
    """Test get sales users endpoint without authentication"""
    response = client.get("/api/v1/users/sales")
    assert response.status_code == 401


def test_get_sales_users_empty_result(client: TestClient, user_headers):
    """Test get sales users endpoint when no sales users exist"""
    response = client.get("/api/v1/users/sales", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_user(client: TestClient, test_user, user_headers):
    """Test get user endpoint"""
    response = client.get(f"/api/v1/users/{test_user['id']}", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]


def test_update_user(client: TestClient, test_user, user_headers):
    """Test update user endpoint"""
    response = client.put(
        f"/api/v1/users/{test_user['id']}",
        headers=user_headers,
        json={
            "full_name": "Updated User Name"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["full_name"] == "Updated User Name"


# Villa API tests
def test_create_villa(client: TestClient, admin_headers, user_headers):
    """Test create villa endpoint"""
    # Test as admin
    response = client.post(
        "/api/v1/villas/",
        headers=admin_headers,
        json={
            "name": "API Test Villa",
            "description": "Villa created by API test",
            "base_price": 1500000,
            "max_guests": 6,
            "bedrooms": 3,
            "bathrooms": 3
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Test Villa"
    assert data["description"] == "Villa created by API test"
    assert data["base_price"] == 1500000
    assert "id" in data
    
    # Test as regular user (should be forbidden)
    response = client.post(
        "/api/v1/villas/",
        headers=user_headers,
        json={
            "name": "User Villa",
            "description": "Villa created by regular user",
            "base_price": 1000000,
            "max_guests": 4,
            "bedrooms": 2,
            "bathrooms": 2
        }
    )
    assert response.status_code == 403


def test_get_villas(client: TestClient, user_headers, db: Session):
    """Test get villas endpoint"""
    # Create test villas
    villa1 = create_test_villa(db, name="API Villa 1")
    villa2 = create_test_villa(db, name="API Villa 2")
    
    response = client.get("/api/v1/villas/", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    
    # Check if our villas are in the results
    villa_ids = [v["id"] for v in data]
    assert villa1.id in villa_ids
    assert villa2.id in villa_ids


def test_get_villa(client: TestClient, user_headers, db: Session):
    """Test get villa endpoint"""
    # Create test villa
    villa = create_test_villa(db, name="API Get Villa")
    
    response = client.get(f"/api/v1/villas/{villa.id}", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == villa.id
    assert data["name"] == "API Get Villa"


def test_update_villa(client: TestClient, admin_headers, db: Session):
    """Test update villa endpoint"""
    # Create test villa
    villa = create_test_villa(db, name="API Update Villa")
    
    response = client.put(
        f"/api/v1/villas/{villa.id}",
        headers=admin_headers,
        json={
            "name": "Updated Villa Name",
            "description": villa.description,
            "base_price": float(villa.base_price),
            "max_guests": villa.max_guests,
            "bedrooms": villa.bedrooms,
            "bathrooms": villa.bathrooms
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == villa.id
    assert data["name"] == "Updated Villa Name"


def test_check_villa_availability(client: TestClient, user_headers, db: Session):
    """Test check villa availability endpoint"""
    # Create test villa
    villa = create_test_villa(db)
    
    # Check availability
    today = date.today()
    tomorrow = today + timedelta(days=1)
    response = client.post(
        "/api/v1/villas/check-availability",
        headers=user_headers,
        json={
            "villa_id": villa.id,
            "check_in": today.isoformat(),
            "check_out": tomorrow.isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_available"] is True
    
    # Create booking for the villa
    booking = create_test_booking(
        db,
        check_in=today,
        check_out=tomorrow
    )
    from app.tests.utils import create_test_booking_villa
    create_test_booking_villa(db, booking.id, villa.id)
    
    # Check availability again
    response = client.post(
        "/api/v1/villas/check-availability",
        headers=user_headers,
        json={
            "villa_id": villa.id,
            "check_in": today.isoformat(),
            "check_out": tomorrow.isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_available"] is False


# Booking API tests
def test_create_booking(client: TestClient, user_headers, db: Session):
    """Test create booking endpoint"""
    # Create test villa
    villa = create_test_villa(db)
    
    # Create booking
    today = date.today()
    tomorrow = today + timedelta(days=1)
    response = client.post(
        "/api/v1/bookings/",
        headers=user_headers,
        json={
            "guest_name": "API Booking Guest",
            "guest_email": "apibooking@example.com",
            "guest_phone": "+1234567890",
            "check_in": today.isoformat(),
            "check_out": tomorrow.isoformat(),
            "total_pax": 2,
            "notes": "API booking test",
            "villas": [{"villa_id": villa.id}],
            "packages": [],
            "addons": []
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["guest_name"] == "API Booking Guest"
    assert data["guest_email"] == "apibooking@example.com"
    assert data["check_in"] == today.isoformat()
    assert data["check_out"] == tomorrow.isoformat()
    assert data["status"] == "pending"
    assert "id" in data
    assert "booking_code" in data


def test_get_bookings(client: TestClient, user_headers, db: Session):
    """Test get bookings endpoint"""
    # Create test bookings
    booking1 = create_test_booking(db, guest_name="API Booking 1")
    booking2 = create_test_booking(db, guest_name="API Booking 2")
    
    response = client.get("/api/v1/bookings/", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    
    # Check if our bookings are in the results
    booking_ids = [b["id"] for b in data]
    assert booking1.id in booking_ids
    assert booking2.id in booking_ids
    
    # Test filtering by guest name
    response = client.get(
        "/api/v1/bookings/?guest_name=API%20Booking%201",
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(b["guest_name"] == "API Booking 1" for b in data)
    assert not any(b["guest_name"] == "API Booking 2" for b in data)


def test_get_booking(client: TestClient, user_headers, db: Session):
    """Test get booking endpoint"""
    # Create test booking
    booking = create_test_booking(db, guest_name="API Get Booking")
    
    response = client.get(f"/api/v1/bookings/{booking.id}", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == booking.id
    assert data["guest_name"] == "API Get Booking"
    assert data["booking_code"] == booking.booking_code


def test_update_booking_status(client: TestClient, user_headers, db: Session):
    """Test update booking status endpoint"""
    # Create test booking
    booking = create_test_booking(db, guest_name="API Status Booking")
    assert booking.status == "pending"
    
    response = client.patch(
        f"/api/v1/bookings/{booking.id}/status",
        headers=user_headers,
        json={
            "status": "confirmed"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == booking.id
    assert data["status"] == "confirmed"


def test_get_booking_details(client: TestClient, user_headers, test_user, db: Session):
    """Test get booking details endpoint"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    booking = test_data["booking"]
    
    response = client.get(
        f"/api/v1/bookings/{booking.id}/details",
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["booking"]["id"] == booking.id
    assert "total_price" in data
    assert "total_paid" in data
    assert "balance" in data


# Payment API tests
def test_create_payment(client: TestClient, user_headers, db: Session):
    """Test create payment endpoint"""
    # Create test booking
    booking = create_test_booking(db)
    
    # Create payment
    response = client.post(
        "/api/v1/payments/",
        headers=user_headers,
        json={
            "booking_id": booking.id,
            "amount": 1000000,
            "payment_method": "credit_card",
            "payment_date": datetime.utcnow().isoformat(),
            "notes": "API payment test"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["booking_id"] == booking.id
    assert data["amount"] == 1000000
    assert data["payment_method"] == "credit_card"
    assert data["status"] == "pending"
    assert data["notes"] == "API payment test"
    assert "id" in data


def test_get_payments(client: TestClient, user_headers, db: Session):
    """Test get payments endpoint"""
    # Create test bookings and payments
    booking1 = create_test_booking(db, guest_name="API Payment 1")
    booking2 = create_test_booking(db, guest_name="API Payment 2")
    payment1 = create_test_payment(db, booking1.id, payment_method="bank_transfer")
    payment2 = create_test_payment(db, booking2.id, payment_method="credit_card")
    
    response = client.get("/api/v1/payments/", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    
    # Check if our payments are in the results
    payment_ids = [p["id"] for p in data]
    assert payment1.id in payment_ids
    assert payment2.id in payment_ids
    
    # Test filtering by payment method
    response = client.get(
        "/api/v1/payments/?payment_method=bank_transfer",
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(p["payment_method"] == "bank_transfer" for p in data)
    assert not any(p["payment_method"] == "credit_card" for p in data)


def test_get_payment(client: TestClient, user_headers, db: Session):
    """Test get payment endpoint"""
    # Create test booking and payment
    booking = create_test_booking(db)
    payment = create_test_payment(db, booking.id)
    
    response = client.get(f"/api/v1/payments/{payment.id}", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payment.id
    assert data["booking_id"] == booking.id
    assert data["amount"] == 1000000
    assert data["payment_method"] == "bank_transfer"


def test_update_payment_status(client: TestClient, user_headers, db: Session):
    """Test update payment status endpoint"""
    # Create test booking and payment
    booking = create_test_booking(db)
    payment = create_test_payment(db, booking.id)
    assert payment.status == "pending"
    
    response = client.patch(
        f"/api/v1/payments/{payment.id}/status",
        headers=user_headers,
        json={
            "status": "paid"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == payment.id
    assert data["status"] == "paid"


def test_create_invoice(client: TestClient, user_headers, db: Session):
    """Test create invoice endpoint"""
    # Create test booking
    booking = create_test_booking(db)
    
    # Create invoice
    response = client.post(
        "/api/v1/payments/invoices",
        headers=user_headers,
        json={
            "booking_id": booking.id,
            "guest_name": booking.guest_name,
            "guest_email": booking.guest_email,
            "guest_phone": booking.guest_phone,
            "due_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "description": "Villa Stay",
                    "price": 1000000,
                    "quantity": 1
                }
            ],
            "notes": "API invoice test"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["booking_id"] == booking.id
    assert data["guest_name"] == booking.guest_name
    assert data["total_amount"] == 1000000
    assert data["status"] == "pending"
    assert data["notes"] == "API invoice test"
    assert "id" in data
    assert "invoice_number" in data


def test_get_booking_payment_summary(client: TestClient, user_headers, test_user, db: Session):
    """Test get booking payment summary endpoint"""
    # Create complete booking
    test_data = create_complete_test_booking(db, test_user["id"])
    booking = test_data["booking"]
    
    response = client.get(
        f"/api/v1/payments/bookings/{booking.id}/summary",
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["booking_id"] == booking.id
    assert data["booking_code"] == booking.booking_code
    assert data["guest_name"] == booking.guest_name
    assert "total_invoiced" in data
    assert "total_paid" in data
    assert "balance" in data
    assert "payments" in data
    assert "invoices" in data


# Report API tests
def test_get_dashboard_summary(client: TestClient, user_headers, test_user, db: Session):
    """Test get dashboard summary endpoint"""
    # Create complete booking
    create_complete_test_booking(db, test_user["id"])
    
    response = client.get("/api/v1/reports/dashboard", headers=user_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_bookings" in data
    assert "pending_bookings" in data
    assert "ongoing_bookings" in data
    assert "completed_bookings" in data
    assert "cancelled_bookings" in data
    assert "total_revenue" in data
    assert "pending_payments" in data
    assert "occupancy_rate" in data
    assert "top_villas" in data
    assert "recent_bookings" in data
    assert "revenue_chart" in data


def test_get_villa_occupancy_report(client: TestClient, user_headers, test_user, db: Session):
    """Test get villa occupancy report endpoint"""
    # Create complete booking
    create_complete_test_booking(db, test_user["id"])
    
    response = client.post(
        "/api/v1/reports/villa-occupancy",
        headers=user_headers,
        json={
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "villa_id": None  # All villas
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data
    assert "total_days" in data
    assert "villas" in data
    assert "average_occupancy_rate" in data
    assert "total_revenue" in data
    assert len(data["villas"]) > 0


def test_get_booking_status_report(client: TestClient, user_headers, test_user, db: Session):
    """Test get booking status report endpoint"""
    # Create complete booking
    create_complete_test_booking(db, test_user["id"])
    
    response = client.post(
        "/api/v1/reports/booking-status",
        headers=user_headers,
        json={
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "status": None  # All statuses
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data
    assert "total_bookings" in data
    assert "status_breakdown" in data
    assert len(data["status_breakdown"]) > 0


def test_get_revenue_report(client: TestClient, user_headers, test_user, db: Session):
    """Test get revenue report endpoint"""
    # Create complete booking with paid payment
    test_data = create_complete_test_booking(db, test_user["id"])
    payment = test_data["payment"]
    payment.status = "paid"
    
    response = client.post(
        "/api/v1/reports/revenue",
        headers=user_headers,
        json={
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "end_date": (date.today() + timedelta(days=30)).isoformat(),
            "group_by": "day"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data
    assert "group_by" in data
    assert "total_revenue" in data
    assert "total_bookings" in data
    assert "average_booking_value" in data
    assert "items" in data


def test_get_top_villas_report(client: TestClient, user_headers, test_user, db: Session):
    """Test get top villas report endpoint"""
    # Create complete booking
    create_complete_test_booking(db, test_user["id"])
    
    response = client.get(
        f"/api/v1/reports/top-villas?start_date={(date.today() - timedelta(days=30)).isoformat()}&end_date={(date.today() + timedelta(days=30)).isoformat()}&limit=5",
        headers=user_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "start_date" in data
    assert "end_date" in data
    assert "villas" in data
    assert len(data["villas"]) > 0