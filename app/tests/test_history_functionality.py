"""
Comprehensive tests for history tracking functionality

This test suite covers:
- Quote history tracking (creation, updates, status changes, deletion)
- Booking history tracking (creation, updates, villas, items, status changes)
- Payment history tracking (creation, updates, status changes, deletion)
- History relationships and metadata structure
- Error handling in safe logging wrappers
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.quote import Quote, QuoteItem, QuoteVilla, QuoteHistory
from app.models.booking import Booking, BookingItem, BookingVilla, BookingHistory
from app.models.payment import Payment, Invoice, InvoiceItem, PaymentHistory
from app.services import quote as quote_service
from app.services import booking as booking_service
from app.services import payment as payment_service


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def admin_user(db: Session) -> User:
    """Create an admin user for testing"""
    admin = User(
        username="admin@tugugroup.co.id",
        email="admin@tugugroup.co.id",
        full_name="Test Admin",
        password_hash="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # password: 1q2w3e4r5t
        is_active=True,
        role='admin'
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def test_customer(db: Session, admin_user: User) -> Customer:
    """Create a test customer"""
    customer = Customer(
        user_id=admin_user.id,
        name="Test Customer",
        email="customer@test.com",
        phone_number="6281234567890",
        address="Test Address",
        billing_address="Test Billing Address",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@pytest.fixture
def test_package(db: Session, admin_user: User) -> Package:
    """Create a test package"""
    package = Package(
        user_id=admin_user.id,
        name="Test Package",
        category="Adventure",
        type="Tour",
        description="Test package for history tests",
        days=1,
        cost_per_pax=Decimal("500000.00"),
        min_pax=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    return package


@pytest.fixture
def test_villa(db: Session) -> Villa:
    """Create a test villa"""
    villa = Villa(
        name="Test Villa",
        capacity="4",
        base_price=Decimal("1000000.00"),
        location="Bali",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    return villa


# ============================================================================
# TestQuoteHistory
# ============================================================================

class TestQuoteHistory:
    """Test quote history tracking functionality"""
    
    def test_quote_creation_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that creating a quote logs a history entry."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-001",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total_price=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        # Log history
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            event_type="quote_created",
            user_id=admin_user.id,
            event_category="lifecycle",
            description="Quote created",
            metadata={"initial_status": "draft"}
        )
        
        # Verify history exists
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote.id,
            QuoteHistory.event_type == "quote_created"
        ).first()
        
        assert history is not None
        assert history.user_id == admin_user.id
        assert history.quote_id == quote.id
        assert "initial_status" in history.event_metadata
        assert history.event_metadata["initial_status"] == "draft"
        assert history.event_category == "lifecycle"
    
    def test_quote_update_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that updating a quote logs history entry with changed fields."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-002",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        # Update quote
        old_total = quote.total
        quote.total = Decimal("1500.00")
        quote.notes = "Updated notes"
        db.commit()
        
        # Log history
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            user_id=admin_user.id,
            event_type="quote_updated",
            event_category="data",
            description="Quote updated",
            metadata={
                "changed_fields": {
                    "total": str(quote.total),
                    "notes": quote.notes
                },
                "old_total": str(old_total)
            }
        )
        
        # Verify history entry has changed_fields metadata
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote.id,
            QuoteHistory.event_type == "quote_updated"
        ).first()
        
        assert history is not None
        assert "changed_fields" in history.event_metadata
        assert "total" in history.event_metadata["changed_fields"]
        assert history.event_category == "data"
    
    def test_quote_status_change_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that changing quote status logs it."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-003",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        # Change status
        old_status = quote.status
        quote.status = "sent"
        db.commit()
        
        # Log status change
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            user_id=admin_user.id,
            event_type="status_changed",
            event_category="status",
            description=f"Quote status changed from '{old_status}' to '{quote.status}'",
            metadata={
                "old_status": old_status,
                "new_status": quote.status
            }
        )
        
        # Verify history
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote.id,
            QuoteHistory.event_type == "status_changed"
        ).first()
        
        assert history is not None
        assert history.event_metadata["old_status"] == "draft"
        assert history.event_metadata["new_status"] == "sent"
        assert history.event_category == "status"
    
    def test_quote_deletion_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that deleting a quote records deletion."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-004",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        quote_id = quote.id
        
        # Log deletion before actual deletion
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            user_id=admin_user.id,
            event_type="quote_deleted",
            event_category="lifecycle",
            description="Quote deleted",
            metadata={
                "quote_number": quote.quote_number,
                "status": quote.status
            }
        )
        
        # Verify history before deletion
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote_id,
            QuoteHistory.event_type == "quote_deleted"
        ).first()
        
        assert history is not None
        assert history.event_metadata["quote_number"] == "QT-TEST-004"
        assert history.event_category == "lifecycle"
    
    def test_quote_history_has_relationships(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that quote_history.quote and quote_history.user relationships work."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-005",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        # Log history
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            user_id=admin_user.id,
            event_type="quote_created",
            event_category="lifecycle",
            description="Quote created",
            metadata={}
        )
        
        # Verify relationships
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote.id
        ).first()
        
        assert history is not None
        assert history.quote is not None
        assert history.quote.id == quote.id
        assert history.user is not None
        assert history.user.id == admin_user.id
    
    def test_quote_history_metadata_structure(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that event_metadata JSON contains expected keys."""
        # Create quote
        quote = Quote(
            customer_id=test_customer.id,
            user_id=admin_user.id,
            quote_number="QT-TEST-006",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=30),
            total=Decimal("1000.00"),
            status="draft"
        )
        db.add(quote)
        db.commit()
        db.refresh(quote)
        
        # Log history with specific metadata
        expected_metadata = {
            "quote_number": quote.quote_number,
            "customer_name": test_customer.name,
            "total_amount": str(quote.total),
            "status": quote.status
        }
        
        quote_service.safe_log_quote_history(
            db=db,
            quote_id=quote.id,
            user_id=admin_user.id,
            event_type="quote_created",
            event_category="lifecycle",
            description="Quote created",
            metadata=expected_metadata
        )
        
        # Verify metadata structure
        history = db.query(QuoteHistory).filter(
            QuoteHistory.quote_id == quote.id
        ).first()
        
        assert history is not None
        assert history.event_metadata is not None
        assert "quote_number" in history.event_metadata
        assert "customer_name" in history.event_metadata
        assert "total_amount" in history.event_metadata
        assert "status" in history.event_metadata
    
    def test_safe_log_quote_history_handles_errors(
        self, db: Session, admin_user: User
    ):
        """Test that error handling doesn't break operations."""
        # Try to log history with invalid quote_id
        # Should not raise exception due to safe wrapper
        result = quote_service.safe_log_quote_history(
            db=db,
            quote_id=99999,  # Non-existent
            user_id=admin_user.id,
            event_type="test_event",
            event_category="lifecycle",
            description="Test error handling",
            metadata={}
        )
        
        # Should return None on error but not crash
        assert result is None


# ============================================================================
# TestBookingHistory
# ============================================================================

class TestBookingHistory:
    """Test booking history tracking functionality"""
    
    def test_booking_creation_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that creating a booking logs a history entry."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-001",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00"),
            amount_paid=Decimal("0.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log history
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="created",
            field_name="status",
            old_value=None,
            new_value=booking.status
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "created"
        ).first()
        
        assert history is not None
        assert history.user_id == admin_user.id
        assert history.booking_id == booking.id
        assert history.new_value == "pending"
    
    def test_booking_update_logs_field_changes(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that updating a booking logs field changes."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-002",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Update booking
        old_pax = booking.total_pax
        booking.total_pax = 4
        db.commit()
        
        # Log field change
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="field_update",
            field_name="total_pax",
            old_value=str(old_pax),
            new_value=str(booking.total_pax)
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "field_update",
            BookingHistory.field_name == "total_pax"
        ).first()
        
        assert history is not None
        assert history.old_value == "2"
        assert history.new_value == "4"
    
    def test_booking_status_change_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that changing booking status logs it."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-003",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Change status
        old_status = booking.status
        booking.status = "confirmed"
        db.commit()
        
        # Log status change
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="status_change",
            field_name="status",
            old_value=old_status,
            new_value=booking.status
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "status_change"
        ).first()
        
        assert history is not None
        assert history.old_value == "pending"
        assert history.new_value == "confirmed"
    
    def test_booking_villa_addition_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer, test_villa: Villa
    ):
        """Test that adding a villa logs "villa_added" event."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-004",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log villa addition
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="villa_added",
            field_name="villas",
            old_value=None,
            new_value=f"Added villa: {test_villa.name}"
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "villa_added"
        ).first()
        
        assert history is not None
        assert "villa" in history.new_value.lower()
    
    def test_booking_villa_removal_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer, test_villa: Villa
    ):
        """Test that removing a villa logs "villa_removed" event."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-005",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log villa removal
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="villa_removed",
            field_name="villas",
            old_value=f"Villa: {test_villa.name}",
            new_value=None
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "villa_removed"
        ).first()
        
        assert history is not None
        assert "villa" in history.old_value.lower()
    
    def test_booking_item_addition_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer, test_package: Package
    ):
        """Test that adding an item logs "item_added" event."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-006",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log item addition
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="item_added",
            field_name="items",
            old_value=None,
            new_value=f"Added item: {test_package.name}"
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "item_added"
        ).first()
        
        assert history is not None
        assert "item" in history.new_value.lower()
    
    def test_booking_item_removal_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that removing an item logs "item_removed" event."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-007",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log item removal
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="item_removed",
            field_name="items",
            old_value="Item 123",
            new_value=None
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "item_removed"
        ).first()
        
        assert history is not None
        assert history.old_value is not None
        assert history.new_value is None
    
    def test_booking_payment_association_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that associating a payment logs payment_id."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-008",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("3000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("1000000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="completed"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Log payment association
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="payment_received",
            field_name="payment",
            old_value=None,
            new_value=f"Payment {payment.id}",
            payment_id=payment.id
        )
        
        # Verify history with payment_id
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id,
            BookingHistory.change_type == "payment_received"
        ).first()
        
        assert history is not None
        assert history.payment_id == payment.id
    
    def test_booking_deletion_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that deleting a booking logs deletion."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-009",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        booking_id = booking.id
        
        # Log deletion
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="deleted",
            field_name="status",
            old_value=booking.status,
            new_value=None
        )
        
        # Verify history
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking_id,
            BookingHistory.change_type == "deleted"
        ).first()
        
        assert history is not None
        assert history.old_value == "pending"
    
    def test_booking_history_has_relationships(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that booking history relationships work."""
        # Create booking
        booking = Booking(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            booking_code="BK-TEST-010",
            check_in=date.today() + timedelta(days=7),
            check_out=date.today() + timedelta(days=10),
            total_pax=2,
            status="pending",
            total=Decimal("3000000.00")
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        
        # Log history
        booking_service.safe_log_booking_history(
            db=db,
            booking_id=booking.id,
            user_id=admin_user.id,
            change_type="created",
            field_name="status",
            old_value=None,
            new_value="pending"
        )
        
        # Verify relationships
        history = db.query(BookingHistory).filter(
            BookingHistory.booking_id == booking.id
        ).first()
        
        assert history is not None
        assert history.booking is not None
        assert history.booking.id == booking.id
        assert history.user is not None
        assert history.user.id == admin_user.id
    
    def test_safe_log_booking_history_handles_errors(
        self, db: Session, admin_user: User
    ):
        """Test that error handling doesn't break operations."""
        # Try to log history with invalid booking_id
        result = booking_service.safe_log_booking_history(
            db=db,
            booking_id=99999,  # Non-existent
            user_id=admin_user.id,
            change_type="test_event",
            field_name="test",
            old_value=None,
            new_value="test"
        )
        
        # Should return None on error but not crash
        assert result is None


# ============================================================================
# TestPaymentHistory
# ============================================================================

class TestPaymentHistory:
    """Test payment history tracking functionality"""
    
    def test_payment_creation_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that creating a payment logs a history entry."""
        # Create invoice
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        # Create payment
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="pending"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Log history
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="payment_created",
            event_category="lifecycle",
            description=f"Payment created for ${payment.amount}",
            metadata={
                "amount": str(payment.amount),
                "payment_method": payment.payment_method,
                "status": payment.status
            }
        )
        
        # Verify history
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.event_type == "payment_created"
        ).first()
        
        assert history is not None
        assert history.user_id == admin_user.id
        assert history.payment_id == payment.id
        assert "amount" in history.event_metadata
        assert history.event_category == "lifecycle"
    
    def test_payment_update_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that updating a payment logs changed fields."""
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-002",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="pending",
            notes="Initial notes"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Update payment
        old_notes = payment.notes
        payment.notes = "Updated notes"
        db.commit()
        
        # Log update
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="payment_updated",
            event_category="data",
            description="Payment updated",
            metadata={
                "changed_fields": {
                    "notes": {
                        "old": old_notes,
                        "new": payment.notes
                    }
                }
            }
        )
        
        # Verify history
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.event_type == "payment_updated"
        ).first()
        
        assert history is not None
        assert "changed_fields" in history.event_metadata
        assert history.event_category == "data"
    
    def test_payment_status_change_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that changing payment status logs it."""
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-003",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("1000000.00"),
            payment_method="bank_transfer",
            payment_type="paid-off",
            payment_date=date.today(),
            status="pending"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Change status
        old_status = payment.status
        payment.status = "completed"
        db.commit()
        
        # Log status change
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="status_changed",
            event_category="status",
            description=f"Payment status changed from '{old_status}' to '{payment.status}'",
            metadata={
                "old_status": old_status,
                "new_status": payment.status,
                "amount": str(payment.amount)
            }
        )
        
        # Verify history
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id,
            PaymentHistory.event_type == "status_changed"
        ).first()
        
        assert history is not None
        assert history.event_metadata["old_status"] == "pending"
        assert history.event_metadata["new_status"] == "completed"
        assert history.event_category == "status"
    
    def test_payment_deletion_logs_history(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that deleting a payment logs deletion."""
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-004",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("250000.00"),
            payment_method="cash",
            payment_type="down-payment",
            payment_date=date.today(),
            status="pending"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        payment_id = payment.id
        
        # Log deletion
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="payment_deleted",
            event_category="lifecycle",
            description=f"Payment of ${payment.amount} deleted",
            metadata={
                "amount": str(payment.amount),
                "payment_method": payment.payment_method,
                "status": payment.status
            }
        )
        
        # Verify history
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment_id,
            PaymentHistory.event_type == "payment_deleted"
        ).first()
        
        assert history is not None
        assert "amount" in history.event_metadata
        assert history.event_category == "lifecycle"
    
    def test_payment_history_has_relationships(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that payment history relationships work."""
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-005",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("500000.00"),
            payment_method="bank_transfer",
            payment_type="down-payment",
            payment_date=date.today(),
            status="pending"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Log history
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="payment_created",
            event_category="lifecycle",
            description="Payment created",
            metadata={}
        )
        
        # Verify relationships
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id
        ).first()
        
        assert history is not None
        assert history.payment is not None
        assert history.payment.id == payment.id
        assert history.user is not None
        assert history.user.id == admin_user.id
    
    def test_payment_history_metadata_structure(
        self, db: Session, admin_user: User, test_customer: Customer
    ):
        """Test that payment history metadata has expected structure."""
        # Create invoice and payment
        invoice = Invoice(
            user_id=admin_user.id,
            customer_id=test_customer.id,
            invoice_number="INV-TEST-006",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status="sent",
            total=Decimal("1000000.00")
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        payment = Payment(
            created_by=admin_user.id,
            invoice_id=invoice.id,
            amount=Decimal("1000000.00"),
            payment_method="credit_card",
            payment_type="paid-off",
            payment_date=date.today(),
            status="completed"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
        # Log with structured metadata
        expected_metadata = {
            "amount": str(payment.amount),
            "payment_method": payment.payment_method,
            "payment_type": payment.payment_type,
            "invoice_id": payment.invoice_id,
            "status": payment.status
        }
        
        payment_service.safe_log_payment_history(
            db=db,
            payment_id=payment.id,
            user_id=admin_user.id,
            event_type="payment_created",
            event_category="lifecycle",
            description="Payment created",
            metadata=expected_metadata
        )
        
        # Verify metadata structure
        history = db.query(PaymentHistory).filter(
            PaymentHistory.payment_id == payment.id
        ).first()
        
        assert history is not None
        assert history.event_metadata is not None
        assert "amount" in history.event_metadata
        assert "payment_method" in history.event_metadata
        assert "payment_type" in history.event_metadata
        assert "status" in history.event_metadata
    
    def test_safe_log_payment_history_handles_errors(
        self, db: Session, admin_user: User
    ):
        """Test that error handling doesn't break operations."""
        # Try to log history with invalid payment_id
        result = payment_service.safe_log_payment_history(
            db=db,
            payment_id=99999,  # Non-existent
            user_id=admin_user.id,
            event_type="test_event",
            event_category="lifecycle",
            description="Test error handling",
            metadata={}
        )
        
        # Should return None on error but not crash
        assert result is None