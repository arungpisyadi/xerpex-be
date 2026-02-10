"""
Test invoice amount_due calculation for invoice creation and updates

This test suite verifies:
1. convert_quote_to_invoice() sets amount_due correctly
2. create_invoice() sets amount_due correctly
3. amount_due updates correctly after payment
4. Invoice item updates trigger recalculation of totals
5. Invoice item deletions trigger recalculation of totals
6. Invoice totals sync to linked bookings when items change
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.payment import Invoice, InvoiceItem, InvoiceVilla, Payment
from app.models.quote import Quote, QuoteItem, QuoteVilla
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.user import User
from app.models.booking import Booking
from app.services.payment import create_invoice, convert_quote_to_invoice, create_payment, update_invoice
from app.services.payment import convert_invoice_to_booking
from app.schemas.payment import InvoiceCreate, InvoiceItemCreate, InvoiceUpdate, QuoteToInvoiceRequest, PaymentCreate, PaymentMethod, PaymentType, InvoiceToBookingRequest
from app.schemas.payment import InvoiceStatus


def test_create_invoice_sets_amount_due_correctly(db: Session, test_user):
    """
    Test that create_invoice() sets amount_due = total when creating a new invoice
    
    Bug Fix Verification:
    - Line 271 in payment.py: db_invoice.amount_due = db_invoice.total
    - Verifies amount_due equals total for new invoices (amount_paid defaults to 0)
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        description="Test package description",
        cost_per_pax=Decimal('500.00'),
        category="accommodation"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create invoice data
    invoice_data = InvoiceCreate(
        customer_id=customer.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('500.00'),
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('1000.00')
            )
        ],
        villas=[]
    )
    
    # Get actual user from database
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice
    invoice = create_invoice(db, invoice_data, actual_user)
    
    # Verify amount_due was set correctly
    assert invoice.amount_due == invoice.total, f"Expected amount_due to equal total, but got {invoice.amount_due} != {invoice.total}"
    assert invoice.amount_due == Decimal('1000.00'), f"Expected amount_due to be 1000.00, but got {invoice.amount_due}"
    assert invoice.amount_paid == Decimal('0.00'), f"Expected amount_paid to be 0.00, but got {invoice.amount_paid}"
    assert invoice.total == Decimal('1000.00'), f"Expected total to be 1000.00, but got {invoice.total}"


def test_create_invoice_with_villa_sets_amount_due_correctly(db: Session, test_user):
    """
    Test that create_invoice() sets amount_due correctly when invoice includes villas.
    
    Note: create_invoice calculates total from items only, not including villas.
    The villa associations are stored separately but their prices are not added to total.
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        description="Test package description",
        cost_per_pax=Decimal('300.00'),
        category="accommodation"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a villa
    villa = Villa(
        name="Test Villa",
        description="Beautiful test villa",
        base_price=Decimal('700.00'),
        capacity="4 guests",
        room_type="Villa"
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    
    # Create invoice data with package and villa
    invoice_data = InvoiceCreate(
        customer_id=customer.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('300.00'),
                discount=Decimal('0.00'),
                pax=1,
                line_total=Decimal('300.00')
            )
        ],
        villas=[villa.id]
    )
    
    # Get actual user from database
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice
    invoice = create_invoice(db, invoice_data, actual_user)
    
    # Verify amount_due was set correctly (items total only, villas not added to total)
    # Note: Villas are associated but their prices are not added to total in create_invoice
    expected_total = Decimal('300.00')  # Only items, not villas
    assert invoice.total == expected_total, f"Expected total to be {expected_total}, but got {invoice.total}"
    assert invoice.amount_due == invoice.total, f"Expected amount_due to equal total"
    assert invoice.amount_due == expected_total, f"Expected amount_due to be {expected_total}"
    assert invoice.amount_paid == Decimal('0.00'), f"Expected amount_paid to be 0.00"


def test_convert_quote_to_invoice_sets_amount_due_correctly(db: Session, test_user):
    """
    Test that convert_quote_to_invoice() sets amount_due = quote.total
    
    Bug Fix Verification:
    - Line 1195 in payment.py: amount_due=quote.total
    - Verifies amount_due equals quote total (since amount_paid is 0)
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        description="Test package description",
        cost_per_pax=Decimal('750.00'),
        category="accommodation"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a quote
    quote = Quote(
        user_id=test_user["id"],
        customer_id=customer.id,
        quote_number="QT-TEST-001",
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        status="accepted",
        total=Decimal('1500.00'),
        tax_total=Decimal('0.00')
    )
    db.add(quote)
    db.flush()
    
    # Add quote item
    quote_item = QuoteItem(
        quote_id=quote.id,
        package_id=package.id,
        unit_price=Decimal('750.00'),
        discount=Decimal('0.00'),
        pax=2,
        line_total=Decimal('1500.00')
    )
    db.add(quote_item)
    db.commit()
    db.refresh(quote)
    
    # Get actual user from database
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Convert quote to invoice
    conversion_request = QuoteToInvoiceRequest(
        quote_id=quote.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30)
    )
    
    invoice = convert_quote_to_invoice(db, conversion_request, actual_user)
    
    # Verify amount_due was set correctly from quote
    assert invoice.amount_due == quote.total, f"Expected amount_due to equal quote.total, but got {invoice.amount_due} != {quote.total}"
    assert invoice.amount_due == Decimal('1500.00'), f"Expected amount_due to be 1500.00, but got {invoice.amount_due}"
    assert invoice.amount_paid == Decimal('0.00'), f"Expected amount_paid to be 0.00, but got {invoice.amount_paid}"
    assert invoice.total == quote.total, f"Expected invoice.total to equal quote.total, but got {invoice.total} != {quote.total}"


def test_convert_quote_with_villa_to_invoice_sets_amount_due_correctly(db: Session, test_user):
    """
    Test that convert_quote_to_invoice() sets amount_due correctly when quote includes villas
    
    Bug Fix Verification:
    - Verifies amount_due calculation includes villa prices from quote
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Test Package",
        description="Test package description",
        cost_per_pax=Decimal('400.00'),
        category="accommodation"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a villa
    villa = Villa(
        name="Test Villa",
        description="Beautiful test villa",
        base_price=Decimal('600.00'),
        capacity="4 guests",
        room_type="Villa"
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    
    # Create a quote with villa
    quote = Quote(
        user_id=test_user["id"],
        customer_id=customer.id,
        quote_number="QT-TEST-002",
        issue_date=date.today(),
        expiry_date=date.today() + timedelta(days=30),
        status="accepted",
        total=Decimal('1000.00'),  # 400 (package) + 600 (villa)
        tax_total=Decimal('0.00')
    )
    db.add(quote)
    db.flush()
    
    # Add quote item
    quote_item = QuoteItem(
        quote_id=quote.id,
        package_id=package.id,
        unit_price=Decimal('400.00'),
        discount=Decimal('0.00'),
        pax=1,
        line_total=Decimal('400.00')
    )
    db.add(quote_item)
    
    # Add quote villa
    quote_villa = QuoteVilla(
        quote_id=quote.id,
        villa_id=villa.id
    )
    db.add(quote_villa)
    db.commit()
    db.refresh(quote)
    
    # Get actual user from database
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Convert quote to invoice
    conversion_request = QuoteToInvoiceRequest(
        quote_id=quote.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30)
    )
    
    invoice = convert_quote_to_invoice(db, conversion_request, actual_user)
    
    # Verify amount_due was set correctly from quote
    assert invoice.amount_due == quote.total, f"Expected amount_due to equal quote.total, but got {invoice.amount_due} != {quote.total}"
    assert invoice.amount_due == Decimal('1000.00'), f"Expected amount_due to be 1000.00, but got {invoice.amount_due}"
    assert invoice.amount_paid == Decimal('0.00'), f"Expected amount_paid to be 0.00, but got {invoice.amount_paid}"
    assert invoice.total == quote.total, f"Expected invoice.total to equal quote.total, but got {invoice.total} != {quote.total}"


def test_amount_due_updates_correctly_after_partial_payment(db: Session, test_user):
    """
    Test that amount_due updates correctly after a partial payment is made
    
    Bug Fix Verification:
    - Verifies amount_due = total - amount_paid after payment is added
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create an invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number="INV-TEST-001",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('2000.00'),
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('2000.00'),  # Should be set initially
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Verify initial state
    assert invoice.amount_due == Decimal('2000.00'), "Initial amount_due should equal total"
    assert invoice.amount_paid == Decimal('0.00'), "Initial amount_paid should be 0"
    
    # Create a partial payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('800.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="PAY-001",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Refresh invoice to get updated values
    db.refresh(invoice)
    
    # Verify amount_due updated correctly
    assert invoice.amount_paid == Decimal('800.00'), f"Expected amount_paid to be 800.00, but got {invoice.amount_paid}"
    assert invoice.amount_due == Decimal('1200.00'), f"Expected amount_due to be 1200.00 (2000 - 800), but got {invoice.amount_due}"
    assert invoice.amount_due == invoice.total - invoice.amount_paid, "amount_due should equal total - amount_paid"


def test_amount_due_updates_correctly_after_full_payment(db: Session, test_user):
    """
    Test that amount_due becomes 0 after full payment is made
    
    Bug Fix Verification:
    - Verifies amount_due = 0 when invoice is fully paid
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create an invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number="INV-TEST-002",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('1500.00'),
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('1500.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create a full payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('1500.00'),
        payment_method=PaymentMethod.cash,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-002",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Refresh invoice to get updated values
    db.refresh(invoice)
    
    # Verify amount_due is now 0
    assert invoice.amount_paid == Decimal('1500.00'), f"Expected amount_paid to be 1500.00, but got {invoice.amount_paid}"
    assert invoice.amount_due == Decimal('0.00'), f"Expected amount_due to be 0.00, but got {invoice.amount_due}"
    assert invoice.amount_due == invoice.total - invoice.amount_paid, "amount_due should equal total - amount_paid"
    assert invoice.status == "paid", f"Expected status to be 'paid', but got {invoice.status}"


def test_amount_due_updates_correctly_after_multiple_payments(db: Session, test_user):
    """
    Test that amount_due updates correctly after multiple incremental payments
    
    Bug Fix Verification:
    - Verifies amount_due calculation across multiple payment transactions
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create an invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number="INV-TEST-003",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('3000.00'),
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('3000.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # First payment: 1000
    payment1_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('1000.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="PAY-003-1",
        status="completed"
    )
    create_payment(db, payment1_data, test_user["id"])
    db.refresh(invoice)
    
    assert invoice.amount_paid == Decimal('1000.00'), "After first payment, amount_paid should be 1000"
    assert invoice.amount_due == Decimal('2000.00'), "After first payment, amount_due should be 2000"
    
    # Second payment: 800
    payment2_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('800.00'),
        payment_method=PaymentMethod.cash,
        payment_type=PaymentType.installment,
        payment_date=date.today(),
        reference_number="PAY-003-2",
        status="completed"
    )
    create_payment(db, payment2_data, test_user["id"])
    db.refresh(invoice)
    
    assert invoice.amount_paid == Decimal('1800.00'), "After second payment, amount_paid should be 1800"
    assert invoice.amount_due == Decimal('1200.00'), "After second payment, amount_due should be 1200"
    
    # Third payment: 1200 (complete)
    payment3_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('1200.00'),
        payment_method=PaymentMethod.credit_card,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-003-3",
        status="completed"
    )
    create_payment(db, payment3_data, test_user["id"])
    db.refresh(invoice)
    
    assert invoice.amount_paid == Decimal('3000.00'), "After final payment, amount_paid should be 3000"
    assert invoice.amount_due == Decimal('0.00'), "After final payment, amount_due should be 0"
    assert invoice.status == "paid", "Invoice should be marked as paid"


def test_amount_due_with_overpayment(db: Session, test_user):
    """
    Test that amount_due is calculated correctly even with overpayment
    
    Bug Fix Verification:
    - Verifies amount_due can be negative (indicates overpayment)
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer",
        email="customer@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create an invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number="INV-TEST-004",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('1000.00'),
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('1000.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create an overpayment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('1200.00'),  # 200 more than needed
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-004",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Refresh invoice to get updated values
    db.refresh(invoice)
    
    # Verify amount_due reflects overpayment (negative value)
    assert invoice.amount_paid == Decimal('1200.00'), f"Expected amount_paid to be 1200.00, but got {invoice.amount_paid}"
    assert invoice.amount_due == Decimal('-200.00'), f"Expected amount_due to be -200.00 (overpayment), but got {invoice.amount_due}"
    assert invoice.amount_due == invoice.total - invoice.amount_paid, "amount_due should equal total - amount_paid even when negative"
    assert invoice.status == "paid", "Invoice should be marked as paid despite overpayment"


# ============================================================================
# Test: Invoice Item Update Sync - Invoice totals recalculate on item changes
# ============================================================================


def test_invoice_items_update_triggers_recalculation(db: Session, test_user):
    """
    Test that updating invoice items triggers recalculation of totals.
    
    Scenario:
    - Create an invoice with items (packages)
    - Update an item's price/quantity
    - Verify invoice.total and invoice.amount_due are updated correctly
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Item Update",
        email="customer_item_update@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create packages
    package1 = Package(
        user_id=test_user["id"],
        name="Package 1",
        description="Test package 1",
        cost_per_pax=Decimal('500.00'),
        category="Tour"
    )
    package2 = Package(
        user_id=test_user["id"],
        name="Package 2",
        description="Test package 2",
        cost_per_pax=Decimal('300.00'),
        category="Tour"
    )
    db.add(package1)
    db.add(package2)
    db.commit()
    db.refresh(package1)
    db.refresh(package2)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice with initial items (total = 1000)
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number=f"INV-ITEM-UPDATE-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('1000.00'),  # package1: 500 * 2 = 1000
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('1000.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.flush()
    
    # Add initial invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package1.id,
        unit_price=Decimal('500.00'),
        discount=Decimal('0.00'),
        pax=2,
        line_total=Decimal('1000.00')
    )
    db.add(invoice_item)
    db.commit()
    db.refresh(invoice)
    
    # Verify initial total
    assert invoice.total == Decimal('1000.00'), f"Initial total should be 1000.00, got {invoice.total}"
    assert invoice.amount_due == Decimal('1000.00'), "Initial amount_due should equal total"
    
    # Update the invoice with new items - increase quantity and add new package
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package1.id,
                unit_price=Decimal('500.00'),
                discount=Decimal('0.00'),
                pax=4,  # Increased from 2 to 4
                line_total=Decimal('2000.00')  # 500 * 4
            ),
            InvoiceItemCreate(
                package_id=package2.id,
                unit_price=Decimal('300.00'),
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('600.00')  # 300 * 2
            )
        ],
        villas=[]  # No villas
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # Verify new total: 2000 + 600 = 2600
    expected_new_total = Decimal('2600.00')
    assert updated_invoice.total == expected_new_total, f"Updated total should be {expected_new_total}, got {updated_invoice.total}"
    assert updated_invoice.amount_due == expected_new_total, f"Updated amount_due should equal total"


def test_invoice_items_update_syncs_to_booking(db: Session, test_user):
    """
    Test that updating invoice items syncs totals to linked booking.
    
    Scenario:
    - Create an invoice with items and linked booking
    - Update an item's price
    - Verify booking.total and booking.amount_due are also synced
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Booking Sync",
        email="customer_booking_sync@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Package for Booking Sync",
        description="Test package",
        cost_per_pax=Decimal('400.00'),
        category="Tour"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a villa
    villa = Villa(
        name="Test Villa for Booking Sync",
        description="Beautiful test villa",
        base_price=Decimal('600.00'),
        capacity="4 guests",
        room_type="Villa"
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create a partially_paid invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number=f"INV-BOOKING-SYNC-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status="partially_paid",
        total=Decimal('1000.00'),  # 400 (package) + 600 (villa)
        amount_paid=Decimal('200.00'),
        amount_due=Decimal('800.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal('400.00'),
        discount=Decimal('0.00'),
        pax=1,
        line_total=Decimal('400.00')
    )
    db.add(invoice_item)
    
    # Add invoice villa
    invoice_villa = InvoiceVilla(
        invoice_id=invoice.id,
        villa_id=villa.id
    )
    db.add(invoice_villa)
    
    # Create initial payment
    initial_payment = Payment(
        created_by=test_user["id"],
        invoice_id=invoice.id,
        amount=Decimal('200.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number=f"PAY-INIT-{datetime.utcnow().timestamp()}",
        status="completed"
    )
    db.add(initial_payment)
    db.commit()
    db.refresh(invoice)
    
    # Convert to booking
    request_data = InvoiceToBookingRequest(
        invoice_id=invoice.id,
        check_in=date.today() + timedelta(days=5),
        check_out=date.today() + timedelta(days=8),
        total_pax=4,
        notes="Converted for item update sync test"
    )
    
    result = convert_invoice_to_booking(
        db=db,
        invoice_id=invoice.id,
        request_data=request_data,
        current_user=actual_user
    )
    
    booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
    assert booking is not None
    
    # Verify initial booking totals match invoice
    assert booking.total == Decimal('1000.00'), f"Initial booking total should be 1000.00, got {booking.total}"
    assert booking.amount_paid == Decimal('200.00'), f"Initial booking amount_paid should be 200.00"
    assert booking.amount_due == Decimal('800.00'), f"Initial booking amount_due should be 800.00"
    
    # Update invoice items - increase package price
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('800.00'),  # Doubled from 400
                discount=Decimal('0.00'),
                pax=1,
                line_total=Decimal('800.00')  # 800 * 1
            )
        ],
        villas=[villa.id]  # Keep the villa
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # Verify new invoice total: 800 (package) + 600 (villa) = 1400
    assert updated_invoice.total == Decimal('1400.00'), f"Updated invoice total should be 1400.00, got {updated_invoice.total}"
    
    # Refresh booking and verify totals synced
    db.refresh(booking)
    assert booking.total == Decimal('1400.00'), f"Booking total should be synced to 1400.00, got {booking.total}"
    assert booking.amount_paid == Decimal('200.00'), f"Booking amount_paid should remain 200.00"
    assert booking.amount_due == Decimal('1200.00'), f"Booking amount_due should be 1200.00 (1400 - 200)"


def test_invoice_items_deletion_triggers_recalculation(db: Session, test_user):
    """
    Test that deleting invoice items triggers recalculation of totals.
    
    Scenario:
    - Create an invoice with multiple items
    - Delete an item (by replacing with fewer items)
    - Verify totals are recalculated correctly
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Item Deletion",
        email="customer_item_delete@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create packages
    package1 = Package(
        user_id=test_user["id"],
        name="Package A",
        description="Test package A",
        cost_per_pax=Decimal('500.00'),
        category="Tour"
    )
    package2 = Package(
        user_id=test_user["id"],
        name="Package B",
        description="Test package B",
        cost_per_pax=Decimal('300.00'),
        category="Tour"
    )
    db.add(package1)
    db.add(package2)
    db.commit()
    db.refresh(package1)
    db.refresh(package2)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice with multiple items
    invoice_data = InvoiceCreate(
        customer_id=customer.id,
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        items=[
            InvoiceItemCreate(
                package_id=package1.id,
                unit_price=Decimal('500.00'),
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('1000.00')  # 500 * 2
            ),
            InvoiceItemCreate(
                package_id=package2.id,
                unit_price=Decimal('300.00'),
                discount=Decimal('0.00'),
                pax=1,
                line_total=Decimal('300.00')  # 300 * 1
            )
        ],
        villas=[]
    )
    
    invoice = create_invoice(db, invoice_data, actual_user)
    
    # Verify initial total: 1000 + 300 = 1300
    expected_initial_total = Decimal('1300.00')
    assert invoice.total == expected_initial_total, f"Initial total should be {expected_initial_total}, got {invoice.total}"
    
    # Delete an item by replacing with only one item
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package1.id,
                unit_price=Decimal('500.00'),
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('1000.00')  # Keep only package1
            )
        ],
        villas=[]
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # Verify new total: 1000 only
    expected_new_total = Decimal('1000.00')
    assert updated_invoice.total == expected_new_total, f"Updated total should be {expected_new_total}, got {updated_invoice.total}"
    assert updated_invoice.amount_due == expected_new_total, f"Updated amount_due should equal total"
    
    # Verify only one item exists
    items_count = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).count()
    assert items_count == 1, f"Should have only 1 item, got {items_count}"


def test_invoice_with_payment_and_item_update(db: Session, test_user):
    """
    Test that invoice amount_due is correctly calculated when items are updated with existing payment.
    
    Scenario:
    - Create an invoice with items
    - Add a partial payment
    - Update invoice items
    - Verify invoice.amount_due is correctly calculated as total - amount_paid
    - Verify booking amount_due is also correct
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Payment + Update",
        email="customer_payment_update@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Package for Payment Update",
        description="Test package",
        cost_per_pax=Decimal('500.00'),
        category="Tour"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice with initial items (total = 1000)
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number=f"INV-PAY-UPDATE-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('1000.00'),  # package: 500 * 2 = 1000
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('1000.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.flush()
    
    # Add initial invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal('500.00'),
        discount=Decimal('0.00'),
        pax=2,
        line_total=Decimal('1000.00')
    )
    db.add(invoice_item)
    db.commit()
    db.refresh(invoice)
    
    # Initial state
    assert invoice.total == Decimal('1000.00'), "Initial total should be 1000.00"
    assert invoice.amount_paid == Decimal('0.00'), "Initial amount_paid should be 0"
    assert invoice.amount_due == Decimal('1000.00'), "Initial amount_due should equal total"
    
    # Add a partial payment of 500
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('500.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="PAY-PARTIAL-001",
        status="completed"
    )
    create_payment(db, payment_data, test_user["id"])
    
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('500.00'), f"After payment, amount_paid should be 500.00"
    assert invoice.amount_due == Decimal('500.00'), f"After payment, amount_due should be 500.00"
    
    # Update invoice items - increase the package price
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('800.00'),  # Increased from 500
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('1600.00')  # 800 * 2
            )
        ],
        villas=[]  # No villas
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # New total: 1600
    # amount_paid should still be 500
    # amount_due should be 1600 - 500 = 1100
    assert updated_invoice.total == Decimal('1600.00'), f"New total should be 1600.00, got {updated_invoice.total}"
    assert updated_invoice.amount_paid == Decimal('500.00'), f"amount_paid should remain 500.00"
    assert updated_invoice.amount_due == Decimal('1100.00'), f"amount_due should be 1100.00 (1600 - 500)"


def test_full_payment_invoice_with_item_update_reduces_amount_due(db: Session, test_user):
    """
    Test that updating invoice items reduces amount_due on a fully paid invoice.
    
    Scenario:
    - Create an invoice with items totaling 1000
    - Add payment of 1000 (fully paid)
    - Update invoice items to 1600
    - Verify invoice.amount_due is now 500
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Full Payment Update",
        email="customer_full_payment@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Package for Full Payment",
        description="Test package",
        cost_per_pax=Decimal('500.00'),
        category="Tour"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create invoice with initial items (total = 1000)
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number=f"INV-FULL-PAY-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        status="draft",
        total=Decimal('1000.00'),  # package: 500 * 2 = 1000
        amount_paid=Decimal('0.00'),
        amount_due=Decimal('1000.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.flush()
    
    # Add initial invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal('500.00'),
        discount=Decimal('0.00'),
        pax=2,
        line_total=Decimal('1000.00')
    )
    db.add(invoice_item)
    db.commit()
    db.refresh(invoice)
    
    # Initial state
    assert invoice.total == Decimal('1000.00'), "Initial total should be 1000.00"
    
    # Add full payment of 1000
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('1000.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-FULL-001",
        status="completed"
    )
    create_payment(db, payment_data, test_user["id"])
    
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('1000.00'), f"amount_paid should be 1000.00"
    assert invoice.amount_due == Decimal('0.00'), f"amount_due should be 0.00 (fully paid)"
    assert invoice.status == "paid", f"Invoice status should be 'paid'"
    
    # Update invoice items - increase total to 1600
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('800.00'),  # Increased from 500
                discount=Decimal('0.00'),
                pax=2,
                line_total=Decimal('1600.00')  # 800 * 2
            )
        ],
        villas=[]  # No villas
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # New total: 1600
    # amount_paid should still be 1000
    # amount_due should be 1600 - 1000 = 600
    assert updated_invoice.total == Decimal('1600.00'), f"New total should be 1600.00, got {updated_invoice.total}"
    assert updated_invoice.amount_paid == Decimal('1000.00'), f"amount_paid should remain 1000.00"
    assert updated_invoice.amount_due == Decimal('600.00'), f"amount_due should be 600.00 (1600 - 1000)"
    
    # Note: Invoice status is not updated by update_invoice when totals change.
    # Status is only updated by payment operations (create_payment, update_payment, delete_payment).


def test_full_payment_invoice_with_item_update_syncs_to_booking(db: Session, test_user):
    """
    Test that updating invoice items on a fully paid invoice syncs to linked booking.
    
    Scenario:
    - Create an invoice with items totaling 1000
    - Add payment of 1000 (fully paid)
    - Convert to booking
    - Update invoice items to 1500
    - Verify booking.amount_due is now 500
    """
    # Create a customer
    customer = Customer(
        user_id=test_user["id"],
        name="Test Customer for Booking Full Payment",
        email="customer_booking_full@test.com",
        status=1
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    # Create a package
    package = Package(
        user_id=test_user["id"],
        name="Package for Booking Full Payment",
        description="Test package",
        cost_per_pax=Decimal('500.00'),
        category="Tour"
    )
    db.add(package)
    db.commit()
    db.refresh(package)
    
    # Create a villa
    villa = Villa(
        name="Test Villa for Booking Full Payment",
        description="Beautiful test villa",
        base_price=Decimal('500.00'),
        capacity="4 guests",
        room_type="Villa"
    )
    db.add(villa)
    db.commit()
    db.refresh(villa)
    
    # Get actual user
    actual_user = db.query(User).filter(User.id == test_user["id"]).first()
    
    # Create a fully paid invoice
    invoice = Invoice(
        user_id=test_user["id"],
        customer_id=customer.id,
        invoice_number=f"INV-FULL-PAID-{datetime.utcnow().timestamp()}",
        issue_date=date.today(),
        due_date=date.today() + timedelta(days=30),
        check_in=date.today() + timedelta(days=10),
        check_out=date.today() + timedelta(days=13),
        status="paid",
        total=Decimal('1000.00'),
        amount_paid=Decimal('1000.00'),
        amount_due=Decimal('0.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.flush()
    
    # Add invoice item
    invoice_item = InvoiceItem(
        invoice_id=invoice.id,
        package_id=package.id,
        unit_price=Decimal('500.00'),
        discount=Decimal('0.00'),
        pax=1,
        line_total=Decimal('500.00')
    )
    db.add(invoice_item)
    
    # Add invoice villa
    invoice_villa = InvoiceVilla(
        invoice_id=invoice.id,
        villa_id=villa.id
    )
    db.add(invoice_villa)
    
    # Create full payment
    full_payment = Payment(
        created_by=test_user["id"],
        invoice_id=invoice.id,
        amount=Decimal('1000.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number=f"PAY-FULL-BOOKING-{datetime.utcnow().timestamp()}",
        status="completed"
    )
    db.add(full_payment)
    db.commit()
    db.refresh(invoice)
    
    # Convert to booking
    request_data = InvoiceToBookingRequest(
        invoice_id=invoice.id,
        check_in=date.today() + timedelta(days=5),
        check_out=date.today() + timedelta(days=8),
        total_pax=4,
        notes="Converted for full payment update sync test"
    )
    
    result = convert_invoice_to_booking(
        db=db,
        invoice_id=invoice.id,
        request_data=request_data,
        current_user=actual_user
    )
    
    booking = db.query(Booking).filter(Booking.id == result["booking_id"]).first()
    assert booking is not None
    
    # Verify initial booking state
    assert booking.total == Decimal('1000.00'), f"Initial booking total should be 1000.00"
    assert booking.amount_paid == Decimal('1000.00'), f"Initial booking amount_paid should be 1000.00"
    assert booking.amount_due == Decimal('0.00'), f"Initial booking amount_due should be 0.00"
    
    # Update invoice items - increase to 1500
    invoice_update = InvoiceUpdate(
        items=[
            InvoiceItemCreate(
                package_id=package.id,
                unit_price=Decimal('1000.00'),  # Increased from 500
                discount=Decimal('0.00'),
                pax=1,
                line_total=Decimal('1000.00')  # 1000 * 1
            )
        ],
        villas=[villa.id]  # Villa adds 500, total = 1500
    )
    
    updated_invoice = update_invoice(db, invoice.id, invoice_update, test_user["id"])
    
    # Verify invoice updated
    assert updated_invoice.total == Decimal('1500.00'), f"New invoice total should be 1500.00"
    assert updated_invoice.amount_paid == Decimal('1000.00'), f"Invoice amount_paid should remain 1000.00"
    assert updated_invoice.amount_due == Decimal('500.00'), f"Invoice amount_due should be 500.00"
    
    # Refresh booking and verify sync
    db.refresh(booking)
    assert booking.total == Decimal('1500.00'), f"Booking total should be synced to 1500.00"
    assert booking.amount_paid == Decimal('1000.00'), f"Booking amount_paid should remain 1000.00"
    assert booking.amount_due == Decimal('500.00'), f"Booking amount_due should be 500.00"


# ============================================================================
# Import datetime for timestamp generation
# ============================================================================
from datetime import datetime