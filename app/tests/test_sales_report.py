"""
Tests for Sales Report API endpoint
"""
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.booking import Booking
from app.models.payment import Invoice
from app.utils.security import get_password_hash


def test_sales_report_endpoint(client: TestClient, db: Session, test_admin: dict, admin_headers: dict):
    """
    Test the POST /api/v1/reports/sales endpoint.

    This test:
    1. Creates test invoices with various payment statuses
    2. Makes a POST request to /api/v1/reports/sales
    3. Verifies the response contains expected fields
    """
    # Create a test customer
    customer = Customer(
        user_id=test_admin["id"],
        name="Test Customer",
        email="customer@test.com",
        phone_number="+62812345678"
    )
    db.add(customer)
    
    # Create a test user (sales person)
    sales_user = User(
        username="salesperson",
        email="sales@test.com",
        full_name="Test Sales Person",
        password_hash=get_password_hash("password"),
        is_active=True,
        role="sales"
    )
    db.add(sales_user)
    db.commit()
    db.refresh(customer)
    db.refresh(sales_user)
    
    # Create test invoices with different payment statuses
    # Invoice 1 - Fully paid (with booking)
    booking1 = Booking(
        user_id=sales_user.id,
        customer_id=customer.id,
        sales_person_id=sales_user.id,
        booking_code="BK001",
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        status="completed",
        total=Decimal("5000000"),
        tax_total=Decimal("500000"),
        amount_paid=Decimal("5500000"),
        amount_due=Decimal("0"),
        total_pax=2
    )
    db.add(booking1)
    db.flush()  # Get the booking ID
    
    invoice1 = Invoice(
        user_id=sales_user.id,
        sales_person_id=sales_user.id,
        customer_id=customer.id,
        booking_id=booking1.id,
        invoice_number="INV001",
        issue_date=date(2025, 5, 1),
        due_date=date(2025, 5, 15),
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        status="paid",
        total=Decimal("5000000"),
        amount_due=Decimal("0"),
        tax_total=Decimal("500000"),
        amount_paid=Decimal("5500000")
    )
    db.add(invoice1)
    
    # Invoice 2 - Partially paid (with booking)
    booking2 = Booking(
        user_id=sales_user.id,
        customer_id=customer.id,
        sales_person_id=sales_user.id,
        booking_code="BK002",
        check_in=date(2025, 7, 1),
        check_out=date(2025, 7, 5),
        status="completed",
        total=Decimal("4000000"),
        tax_total=Decimal("400000"),
        amount_paid=Decimal("2000000"),
        amount_due=Decimal("2400000"),
        total_pax=2
    )
    db.add(booking2)
    db.flush()
    
    invoice2 = Invoice(
        user_id=sales_user.id,
        sales_person_id=sales_user.id,
        customer_id=customer.id,
        booking_id=booking2.id,
        invoice_number="INV002",
        issue_date=date(2025, 6, 15),
        due_date=date(2025, 6, 30),
        check_in=date(2025, 7, 1),
        check_out=date(2025, 7, 5),
        status="partially_paid",
        total=Decimal("4000000"),
        amount_due=Decimal("2400000"),
        tax_total=Decimal("400000"),
        amount_paid=Decimal("2000000")
    )
    db.add(invoice2)
    
    # Invoice 3 - Pending/Draft (standalone - no booking)
    invoice3 = Invoice(
        user_id=sales_user.id,
        sales_person_id=sales_user.id,
        customer_id=customer.id,
        booking_id=None,  # No booking - standalone invoice
        invoice_number="INV003",
        issue_date=date(2025, 8, 1),
        due_date=date(2027, 8, 15),  # Future date so it's "pending" not "overdue"
        check_in=None,
        check_out=None,
        status="draft",
        total=Decimal("3000000"),
        amount_due=Decimal("3300000"),
        tax_total=Decimal("300000"),
        amount_paid=Decimal("0")
    )
    db.add(invoice3)
    
    db.commit()
    
    # Make request to sales report endpoint
    response = client.post(
        "/api/v1/reports/sales",
        headers=admin_headers,
        json={
            "start_date": "2025-01-01",
            "end_date": "2028-12-31"
        }
    )
    
    assert response.status_code == 200, f"Response: {response.text}"
    data = response.json()
    
    # Verify response structure
    assert "start_date" in data
    assert "end_date" in data
    assert data["start_date"] == "2025-01-01"
    assert data["end_date"] == "2028-12-31"
    
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) == 3  # We created 3 invoices
    
    # Verify totals
    assert "total_sales_amount" in data
    assert "total_paid_amount" in data
    assert "total_difference" in data
    
    # Check values (service uses invoice.total)
    # Total sales: 5000000 + 4000000 + 3000000 = 12000000
    expected_total = "12000000.00"
    # Total paid: 5500000 + 2000000 + 0 = 7500000
    expected_paid = "7500000.00"
    # Difference: 12000000 - 7500000 = 4500000
    expected_diff = "4500000.00"
    
    assert data["total_sales_amount"] == expected_total
    assert data["total_paid_amount"] == expected_paid
    assert data["total_difference"] == expected_diff
    
    # Verify invoice 1 - has booking_id
    inv1 = next(item for item in data["items"] if item["invoice_number"] == "INV001")
    assert inv1["booking_id"] is not None
    assert inv1["check_in"] == "2025-06-01"
    assert inv1["check_out"] == "2025-06-05"
    assert inv1["payment_status"] == "paid"
    
    # Verify invoice 3 has no booking info (standalone invoice)
    inv3 = next(item for item in data["items"] if item["invoice_number"] == "INV003")
    assert inv3["booking_id"] is None
    assert inv3["check_in"] is None
    assert inv3["check_out"] is None
    assert inv3["payment_status"] == "pending"


def test_sales_report_with_filters(client: TestClient, db: Session, test_admin: dict, admin_headers: dict):
    """
    Test the POST /api/v1/reports/sales endpoint with filters.
    """
    # Create test data
    customer = Customer(
        user_id=test_admin["id"],
        name="Test Customer",
        email="customer@test.com",
        phone_number="+62812345678"
    )
    db.add(customer)
    
    sales_user1 = User(
        username="salesperson1",
        email="sales1@test.com",
        full_name="Sales Person 1",
        password_hash=get_password_hash("password"),
        is_active=True,
        role="sales"
    )
    sales_user2 = User(
        username="salesperson2",
        email="sales2@test.com",
        full_name="Sales Person 2",
        password_hash=get_password_hash("password"),
        is_active=True,
        role="sales"
    )
    db.add(sales_user1)
    db.add(sales_user2)
    db.commit()
    db.refresh(customer)
    db.refresh(sales_user1)
    db.refresh(sales_user2)
    
    # Invoice with sales_user1 - paid
    invoice1 = Invoice(
        user_id=sales_user1.id,
        sales_person_id=sales_user1.id,
        customer_id=customer.id,
        invoice_number="INV101",
        issue_date=date(2025, 6, 1),
        due_date=date(2025, 6, 15),
        check_in=date(2025, 6, 1),
        check_out=date(2025, 6, 5),
        status="paid",
        total=Decimal("5000000"),
        amount_due=Decimal("0"),
        tax_total=Decimal("500000"),
        amount_paid=Decimal("5500000")
    )
    db.add(invoice1)
    
    # Invoice with sales_user2 - pending (draft status with 0 paid)
    invoice2 = Invoice(
        user_id=sales_user2.id,
        sales_person_id=sales_user2.id,
        customer_id=customer.id,
        invoice_number="INV102",
        issue_date=date(2025, 7, 1),
        due_date=date(2027, 7, 15),  # Future date for pending
        check_in=date(2027, 7, 1),
        check_out=date(2027, 7, 5),
        status="draft",
        total=Decimal("3000000"),
        amount_due=Decimal("3300000"),
        tax_total=Decimal("300000"),
        amount_paid=Decimal("0")
    )
    db.add(invoice2)
    
    db.commit()
    
    # Test filter by sales_person_ids
    response = client.post(
        "/api/v1/reports/sales",
        headers=admin_headers,
        json={
            "start_date": "2025-01-01",
            "end_date": "2028-12-31",
            "sales_person_ids": [sales_user1.id]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["invoice_number"] == "INV101"
    
    # Test filter by payment_status = 'paid'
    response = client.post(
        "/api/v1/reports/sales",
        headers=admin_headers,
        json={
            "start_date": "2025-01-01",
            "end_date": "2028-12-31",
            "payment_status": "paid"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["invoice_number"] == "INV101"
    
    # Test filter by payment_status = 'pending'
    response = client.post(
        "/api/v1/reports/sales",
        headers=admin_headers,
        json={
            "start_date": "2025-01-01",
            "end_date": "2028-12-31",
            "payment_status": "pending"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["invoice_number"] == "INV102"


def test_sales_report_unauthorized(client: TestClient):
    """
    Test the POST /api/v1/reports/sales endpoint without authentication.
    """
    response = client.post(
        "/api/v1/reports/sales",
        json={
            "start_date": "2025-01-01",
            "end_date": "2026-12-31"
        }
    )
    assert response.status_code == 401


def test_sales_report_empty_result(client: TestClient, admin_headers: dict):
    """
    Test the POST /api/v1/reports/sales endpoint with no invoices.
    """
    response = client.post(
        "/api/v1/reports/sales",
        headers=admin_headers,
        json={
            "start_date": "2025-01-01",
            "end_date": "2025-12-31"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 0
    # Decimal values are serialized as strings
    assert data["total_sales_amount"] == "0.00"
    assert data["total_paid_amount"] == "0.00"
    assert data["total_difference"] == "0.00"
