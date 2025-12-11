"""
Test invoice amount_due calculation for invoice creation

This test suite verifies that the amount_due bug fix is working correctly:
1. convert_quote_to_invoice() sets amount_due correctly
2. create_invoice() sets amount_due correctly
3. amount_due updates correctly after payment
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.payment import Invoice, InvoiceItem, Payment
from app.models.quote import Quote, QuoteItem, QuoteVilla
from app.models.customer import Customer
from app.models.package import Package
from app.models.villa import Villa
from app.models.user import User
from app.services.payment import create_invoice, convert_quote_to_invoice, create_payment
from app.schemas.payment import InvoiceCreate, InvoiceItemCreate, QuoteToInvoiceRequest, PaymentCreate, PaymentMethod, PaymentType


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
    Test that create_invoice() sets amount_due correctly when invoice includes villas
    
    Bug Fix Verification:
    - Verifies amount_due calculation includes villa prices
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
    
    # Verify amount_due was set correctly (package + villa)
    expected_total = Decimal('1000.00')  # 300 + 700
    assert invoice.total == expected_total, f"Expected total to be {expected_total}, but got {invoice.total}"
    assert invoice.amount_due == invoice.total, f"Expected amount_due to equal total, but got {invoice.amount_due} != {invoice.total}"
    assert invoice.amount_due == expected_total, f"Expected amount_due to be {expected_total}, but got {invoice.amount_due}"
    assert invoice.amount_paid == Decimal('0.00'), f"Expected amount_paid to be 0.00, but got {invoice.amount_paid}"


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