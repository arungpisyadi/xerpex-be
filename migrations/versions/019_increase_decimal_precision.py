"""Increase DECIMAL precision for quotes and invoices tables

Revision ID: 019
Revises: 018
Create Date: 2025-11-02

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects.mysql import DECIMAL


# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'e5f6g7h8i9j0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase DECIMAL precision from (10,2) to (15,2) for financial columns"""
    
    # Update quotes table columns
    op.alter_column('quotes', 'total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('quotes', 'tax_total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    # Update quote_items table columns
    op.alter_column('quote_items', 'unit_price',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('quote_items', 'discount',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('quote_items', 'line_total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    # Update invoices table columns
    op.alter_column('invoices', 'total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'amount_due',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'amount_paid',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'tax_total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    # Update invoice_items table columns
    op.alter_column('invoice_items', 'unit_price',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('invoice_items', 'discount',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)
    
    op.alter_column('invoice_items', 'line_total',
                    existing_type=DECIMAL(10, 2),
                    type_=DECIMAL(15, 2),
                    existing_nullable=False)


def downgrade() -> None:
    """Revert DECIMAL precision from (15,2) back to (10,2)"""
    
    # Revert quotes table columns
    op.alter_column('quotes', 'total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('quotes', 'tax_total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    # Revert quote_items table columns
    op.alter_column('quote_items', 'unit_price',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('quote_items', 'discount',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('quote_items', 'line_total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    # Revert invoices table columns
    op.alter_column('invoices', 'total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'amount_due',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'amount_paid',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('invoices', 'tax_total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    # Revert invoice_items table columns
    op.alter_column('invoice_items', 'unit_price',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('invoice_items', 'discount',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)
    
    op.alter_column('invoice_items', 'line_total',
                    existing_type=DECIMAL(15, 2),
                    type_=DECIMAL(10, 2),
                    existing_nullable=False)