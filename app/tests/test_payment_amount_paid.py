"""
Test invoice amount_paid update functionality when creating payments
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.models.payment import Invoice, Payment
from app.models.customer import Customer
from app.models.user import User
from app.services.payment import create_payment
from app.schemas.payment import PaymentCreate, PaymentMethod, PaymentType, InvoiceStatus


def test_create_payment_updates_invoice_amount_paid(db: Session, test_user):
    """Test that creating a payment updates invoice amount_paid and amount_due"""
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
        total=Decimal('1000.00'),
        amount_paid=Decimal('0.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create a partial payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('300.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.installment,
        payment_date=date.today(),
        reference_number="PAY-001",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Verify payment was created
    assert payment.id is not None
    assert payment.amount == Decimal('300.00')
    
    # Verify invoice amount_paid was updated
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('300.00')
    assert invoice.amount_due == Decimal('700.00')
    assert invoice.status == InvoiceStatus.partially_paid.value


def test_create_payment_full_amount_marks_invoice_paid(db: Session, test_user):
    """Test that paying full amount marks invoice as paid"""
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
        total=Decimal('500.00'),
        amount_paid=Decimal('0.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create a full payment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('500.00'),
        payment_method=PaymentMethod.cash,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-002",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Verify invoice is marked as paid
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('500.00')
    assert invoice.amount_due == Decimal('0.00')
    assert invoice.status == InvoiceStatus.paid.value


def test_create_multiple_payments_accumulates_amount_paid(db: Session, test_user):
    """Test that multiple payments accumulate in amount_paid"""
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
        total=Decimal('1000.00'),
        amount_paid=Decimal('0.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create first payment
    payment1_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('300.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.down_payment,
        payment_date=date.today(),
        reference_number="PAY-003-1",
        status="completed"
    )
    payment1 = create_payment(db, payment1_data, test_user["id"])
    
    # Verify first payment
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('300.00')
    assert invoice.amount_due == Decimal('700.00')
    assert invoice.status == InvoiceStatus.partially_paid.value
    
    # Create second payment
    payment2_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('400.00'),
        payment_method=PaymentMethod.cash,
        payment_type=PaymentType.installment,
        payment_date=date.today(),
        reference_number="PAY-003-2",
        status="completed"
    )
    payment2 = create_payment(db, payment2_data, test_user["id"])
    
    # Verify accumulated payments
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('700.00')
    assert invoice.amount_due == Decimal('300.00')
    assert invoice.status == InvoiceStatus.partially_paid.value
    
    # Create third payment to complete
    payment3_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('300.00'),
        payment_method=PaymentMethod.credit_card,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-003-3",
        status="completed"
    )
    payment3 = create_payment(db, payment3_data, test_user["id"])
    
    # Verify invoice is now paid
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('1000.00')
    assert invoice.amount_due == Decimal('0.00')
    assert invoice.status == InvoiceStatus.paid.value


def test_create_payment_overpayment_marks_invoice_paid(db: Session, test_user):
    """Test that overpayment still marks invoice as paid"""
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
        total=Decimal('500.00'),
        amount_paid=Decimal('0.00'),
        tax_total=Decimal('0.00')
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    
    # Create an overpayment
    payment_data = PaymentCreate(
        invoice_id=invoice.id,
        amount=Decimal('600.00'),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.paid_off,
        payment_date=date.today(),
        reference_number="PAY-004",
        status="completed"
    )
    
    payment = create_payment(db, payment_data, test_user["id"])
    
    # Verify invoice is marked as paid despite overpayment
    db.refresh(invoice)
    assert invoice.amount_paid == Decimal('600.00')
    assert invoice.amount_due == Decimal('-100.00')  # Negative indicates overpayment
    assert invoice.status == InvoiceStatus.paid.value