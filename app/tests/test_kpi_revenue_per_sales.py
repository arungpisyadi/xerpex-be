"""
Tests for KPI monthly revenue per sales endpoint
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.payment import Invoice, Payment
from app.models.customer import Customer
from app.models.target import Target
from app.utils.security import get_password_hash


def create_test_sales_user(db: Session, username: str, full_name: str, is_active: bool = True):
    """Create a test sales user"""
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=full_name,
        password_hash=get_password_hash("password"),
        role="sales",
        is_active=is_active
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_test_customer(db: Session, user_id: int = 1, name: str = "Test Customer"):
    """Create a test customer"""
    customer = Customer(
        user_id=user_id,
        name=name,
        email=f"{name.lower().replace(' ', '_')}@example.com",
        phone_number="+1234567890",
        address="Test Address"
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def create_test_invoice_with_sales_person(
    db: Session,
    user_id: int,
    sales_person_id: int,
    customer_id: int,
    total: float = 1000000,
    days_ago: int = 0
):
    """Create a test invoice with sales person assignment"""
    issue_date = date.today() - timedelta(days=days_ago)
    due_date = issue_date + timedelta(days=30)
    
    invoice = Invoice(
        user_id=user_id,
        sales_person_id=sales_person_id,
        customer_id=customer_id,
        invoice_number=f"INV-TEST-{datetime.now().timestamp()}",
        issue_date=issue_date,
        due_date=due_date,
        status="paid",
        total=total,
        amount_due=0,
        amount_paid=total,
        tax_total=0
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def create_test_target(
    db: Session,
    user_id: int,
    year: int,
    month: int,
    target_amount: float = 10000000,
    adjusted_target_amount: float | None = None
):
    """Create a test sales target"""
    target = Target(
        user_id=user_id,
        year=year,
        month=month,
        target_amount=target_amount,
        carried_over_amount=0,
        adjusted_target_amount=adjusted_target_amount if adjusted_target_amount else target_amount
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def test_monthly_revenue_per_sales_admin视角(
    client: TestClient, admin_headers, db: Session
):
    """
    Test monthly revenue per sales endpoint as admin
    Admin should see all sales users' performance with target
    """
    from datetime import datetime
    
    # Get current year and month for target
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Create test sales users
    sales_user1 = create_test_sales_user(db, "sales_kpi_1", "Sales Person 1")
    sales_user2 = create_test_sales_user(db, "sales_kpi_2", "Sales Person 2")
    
    # Create test customer
    customer = create_test_customer(db)
    
    # Create invoices for each sales person with current month dates
    invoice1 = create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_user1.id,
        customer_id=customer.id,
        total=5000000,
        days_ago=5
    )
    
    invoice2 = create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_user2.id,
        customer_id=customer.id,
        total=3000000,
        days_ago=3
    )
    
    # Create targets for sales users
    create_test_target(db, sales_user1.id, current_year, current_month, 10000000)
    create_test_target(db, sales_user2.id, current_year, current_month, 8000000)
    
    # Make request as admin
    response = client.get(
        "/api/v1/kpi/monthly_revenue_per_sales",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "month" in data
    assert "year" in data
    assert "sales_performance" in data
    assert isinstance(data["sales_performance"], list)
    
    # Admin should see both sales users
    sales_performance = data["sales_performance"]
    assert len(sales_performance) >= 2
    
    # Verify each sales person has required fields including target
    for sp in sales_performance:
        assert "sales_person_id" in sp
        assert "sales_person_name" in sp
        assert "revenues" in sp
        assert "target" in sp
        assert isinstance(sp["target"], (int, float))
        assert sp["target"] >= 0


def test_monthly_revenue_per_sales_sales用户视角(
    client: TestClient, user_headers, db: Session
):
    """
    Test monthly revenue per sales endpoint as sales user
    Sales user should see only their own performance
    """
    # Create test sales user
    sales_user = create_test_sales_user(db, "sales_kpi_self", "Sales Self Test")
    
    # Create test customer
    customer = create_test_customer(db)
    
    # Create invoice for the sales user
    invoice = create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_user.id,
        customer_id=customer.id,
        total=2500000,
        days_ago=2
    )
    
    # Make request as sales user
    response = client.get(
        "/api/v1/kpi/monthly_revenue_per_sales",
        headers=user_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "month" in data
    assert "year" in data
    assert "sales_performance" in data
    
    # Sales user should see only their own data (at most 1 entry)
    sales_performance = data["sales_performance"]
    assert len(sales_performance) <= 1


def test_monthly_revenue_per_sales_zero_revenue(
    client: TestClient, admin_headers, db: Session
):
    """
    Test monthly revenue per sales endpoint when no invoices exist
    Should return sales users with zero revenue
    """
    # Create test sales users
    sales_user = create_test_sales_user(db, "sales_kpi_zero", "Sales Zero Revenue")
    
    # Make request - no invoices created
    response = client.get(
        "/api/v1/kpi/monthly_revenue_per_sales",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "month" in data
    assert "year" in data
    assert "sales_performance" in data
    
    # Find our test sales user
    sales_performance = data["sales_performance"]
    sales_user_found = False
    for sp in sales_performance:
        if sp["sales_person_id"] == sales_user.id:
            sales_user_found = True
            assert sp["revenues"] == 0.0
            break
    
    # Should have found our sales user
    assert sales_user_found


def test_monthly_revenue_per_sales_unauthorized(
    client: TestClient
):
    """
    Test monthly revenue per sales endpoint without authentication
    Should return 401 Unauthorized
    """
    response = client.get("/api/v1/kpi/monthly_revenue_per_sales")
    assert response.status_code == 401


def test_monthly_revenue_per_sales_response_format(
    client: TestClient, admin_headers, db: Session
):
    """
    Test that response format matches the expected schema including target field
    """
    # Create test sales user
    sales_user = create_test_sales_user(db, "sales_kpi_format", "Sales Format Test")
    
    # Create test customer and invoice
    customer = create_test_customer(db)
    invoice = create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_user.id,
        customer_id=customer.id,
        total=7500000,
        days_ago=1
    )
    
    response = client.get(
        "/api/v1/kpi/monthly_revenue_per_sales",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify month and year are strings
    assert isinstance(data["month"], str)
    assert isinstance(data["year"], str)
    
    # Verify month is a valid month name
    valid_months = ["January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
    assert data["month"] in valid_months
    
    # Verify year is a valid 4-digit year
    assert len(data["year"]) == 4
    assert data["year"].isdigit()
    
    # Verify sales_performance is a list
    assert isinstance(data["sales_performance"], list)
    
    # Verify each entry in sales_performance includes target
    for sp in data["sales_performance"]:
        assert "sales_person_id" in sp
        assert "sales_person_name" in sp
        assert "revenues" in sp
        assert "target" in sp
        assert isinstance(sp["revenues"], (int, float))
        assert isinstance(sp["target"], (int, float))


def test_monthly_revenue_per_sales_with_and_without_targets(
    client: TestClient, admin_headers, db: Session
):
    """
    Test monthly revenue per sales endpoint with and without targets
    Sales users with targets should have target value, those without should have 0
    """
    from datetime import datetime
    
    # Get current year and month for target
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    
    # Create test sales users
    sales_with_target = create_test_sales_user(db, "sales_with_target", "Sales With Target")
    sales_without_target = create_test_sales_user(db, "sales_no_target", "Sales No Target")
    
    # Create test customer
    customer = create_test_customer(db)
    
    # Create invoices for both sales users
    create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_with_target.id,
        customer_id=customer.id,
        total=5000000,
        days_ago=5
    )
    
    create_test_invoice_with_sales_person(
        db,
        user_id=1,
        sales_person_id=sales_without_target.id,
        customer_id=customer.id,
        total=3000000,
        days_ago=3
    )
    
    # Create target only for sales_with_target
    create_test_target(db, sales_with_target.id, current_year, current_month, 10000000)
    
    # Make request as admin
    response = client.get(
        "/api/v1/kpi/monthly_revenue_per_sales",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    sales_performance = data["sales_performance"]
    
    # Find both sales users in response
    sales_with_target_found = False
    sales_without_target_found = False
    
    for sp in sales_performance:
        if sp["sales_person_id"] == sales_with_target.id:
            sales_with_target_found = True
            assert sp["target"] == 10000000.0, "Sales with target should have target value"
            assert sp["revenues"] == 5000000.0
        
        if sp["sales_person_id"] == sales_without_target.id:
            sales_without_target_found = True
            assert sp["target"] == 0.0, "Sales without target should have 0 target"
            assert sp["revenues"] == 3000000.0
    
    # Both sales users should be found
    assert sales_with_target_found, "Sales user with target should be in response"
    assert sales_without_target_found, "Sales user without target should be in response"
