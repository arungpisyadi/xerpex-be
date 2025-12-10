"""
Unit tests for invoice status filter with comma-separated values.
Tests the new functionality for filtering invoices by multiple statuses.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.payment import Invoice, InvoiceItem
from app.models.package import Package
from app.schemas.payment import InvoiceStatus
from app.services.payment import get_invoices


@pytest.fixture
def setup_test_data(db: Session):
    """Setup test data with multiple invoices in different statuses."""
    # Create a test user
    user = User(
        email="test@example.com",
        username="testuser",
        password_hash="testhash",
        role="admin",
        phone="1234567890"
    )
    db.add(user)
    db.flush()
    
    # Create a test customer
    customer = Customer(
        user_id=user.id,
        name="Test Customer",
        email="customer@test.com",
        phone_number="9876543210"
    )
    db.add(customer)
    db.flush()
    
    # Create a test package
    package = Package(
        user_id=user.id,
        name="Test Package",
        description="Test package",
        cost_per_pax=Decimal("100.00"),
        days=1,
        min_pax=1
    )
    db.add(package)
    db.flush()
    
    # Create invoices with different statuses
    statuses = ['draft', 'sent', 'paid', 'overdue', 'cancelled', 'partially_paid']
    invoices = []
    
    for i, status in enumerate(statuses):
        invoice = Invoice(
            user_id=user.id,
            customer_id=customer.id,
            invoice_number=f"INV-TEST-{i+1:03d}",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=status,
            total=Decimal("100.00"),
            tax_total=Decimal("0.00")
        )
        db.add(invoice)
        db.flush()
        
        # Add invoice item
        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            package_id=package.id,
            unit_price=Decimal("100.00"),
            discount=Decimal("0.00"),
            line_total=Decimal("100.00")
        )
        db.add(invoice_item)
        invoices.append(invoice)
    
    db.commit()
    
    return {
        'user': user,
        'customer': customer,
        'package': package,
        'invoices': invoices
    }


def test_filter_single_status(db: Session, setup_test_data):
    """Test filtering invoices by a single status value (backward compatibility)."""
    data = setup_test_data
    user = data['user']
    
    # Test filtering by 'draft' status - pass as a single-item list
    invoices = get_invoices(db=db, current_user=user, status=[InvoiceStatus.draft])
    
    assert len(invoices) == 1
    assert invoices[0].status == 'draft'


def test_filter_multiple_statuses(db: Session, setup_test_data):
    """Test filtering invoices by multiple status values."""
    data = setup_test_data
    user = data['user']
    
    # Test filtering by 'draft', 'sent', and 'paid' statuses
    invoices = get_invoices(
        db=db, 
        current_user=user, 
        status=[InvoiceStatus.draft, InvoiceStatus.sent, InvoiceStatus.paid]
    )
    
    assert len(invoices) == 3
    
    # Verify all returned invoices have one of the requested statuses
    returned_statuses = [inv.status for inv in invoices]
    for status in returned_statuses:
        assert status in ['draft', 'sent', 'paid']


def test_filter_returns_all_when_no_status(db: Session, setup_test_data):
    """Test that no status parameter returns all invoices."""
    data = setup_test_data
    user = data['user']
    
    # Test without status parameter
    invoices = get_invoices(db=db, current_user=user, status=None)
    
    # Should return all invoices (6 total in test data)
    assert len(invoices) == 6


def test_filter_overdue_and_sent(db: Session, setup_test_data):
    """Test filtering by overdue and sent statuses."""
    data = setup_test_data
    user = data['user']
    
    invoices = get_invoices(
        db=db, 
        current_user=user, 
        status=[InvoiceStatus.overdue, InvoiceStatus.sent]
    )
    
    assert len(invoices) == 2
    
    returned_statuses = [inv.status for inv in invoices]
    for status in returned_statuses:
        assert status in ['overdue', 'sent']


def test_filter_all_valid_statuses(db: Session, setup_test_data):
    """Test filtering with all valid status values."""
    data = setup_test_data
    user = data['user']
    
    invoices = get_invoices(
        db=db,
        current_user=user,
        status=[
            InvoiceStatus.draft,
            InvoiceStatus.sent,
            InvoiceStatus.paid,
            InvoiceStatus.overdue,
            InvoiceStatus.cancelled,
            InvoiceStatus.partially_paid
        ]
    )
    
    # Should return all 6 invoices
    assert len(invoices) == 6


def test_filter_with_pagination(db: Session, setup_test_data):
    """Test that status filter works correctly with pagination."""
    data = setup_test_data
    user = data['user']
    
    # Test combining status filter with pagination
    invoices = get_invoices(
        db=db, 
        current_user=user, 
        status=[InvoiceStatus.draft, InvoiceStatus.sent, InvoiceStatus.paid],
        limit=2
    )
    
    # Should be limited to 2 invoices despite 3 matching
    assert len(invoices) == 2


def test_filter_with_empty_list(db: Session, setup_test_data):
    """Test that empty status list returns all invoices."""
    data = setup_test_data
    user = data['user']
    
    # Test with empty status list
    invoices = get_invoices(db=db, current_user=user, status=[])
    
    # Empty list should return all invoices
    assert len(invoices) == 6


def test_backward_compatibility_single_status(db: Session, setup_test_data):
    """Test backward compatibility with single InvoiceStatus enum (not in list)."""
    data = setup_test_data
    user = data['user']
    
    # Test passing a single status value (not in a list) for backward compatibility
    invoices = get_invoices(db=db, current_user=user, status=InvoiceStatus.paid)
    
    assert len(invoices) == 1
    assert invoices[0].status == 'paid'


def test_filter_partially_paid_status(db: Session, setup_test_data):
    """Test filtering by partially_paid status."""
    data = setup_test_data
    user = data['user']
    
    invoices = get_invoices(
        db=db, 
        current_user=user, 
        status=[InvoiceStatus.partially_paid]
    )
    
    assert len(invoices) == 1
    assert invoices[0].status == 'partially_paid'


def test_filter_with_customer_id_and_statuses(db: Session, setup_test_data):
    """Test combining status filter with customer_id filter."""
    data = setup_test_data
    user = data['user']
    customer = data['customer']
    
    # Test combining status filter with customer filter
    invoices = get_invoices(
        db=db,
        current_user=user,
        status=[InvoiceStatus.draft, InvoiceStatus.sent],
        customer_id=customer.id
    )
    
    assert len(invoices) == 2
    for inv in invoices:
        assert inv.customer_id == customer.id
        assert inv.status in ['draft', 'sent']