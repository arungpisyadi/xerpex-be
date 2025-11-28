"""Add check_in and check_out dates to quotes and invoices

Revision ID: 027
Revises: 026
Create Date: 2025-11-28

This migration adds check_in and check_out date columns to both
quotes and invoices tables to support booking date tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'v7w8x9y0z1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add check_in and check_out date columns to quotes and invoices"""
    
    # Add check_in and check_out to quotes table
    op.add_column('quotes', sa.Column('check_in', sa.Date(), nullable=True))
    op.add_column('quotes', sa.Column('check_out', sa.Date(), nullable=True))
    
    # Add check_in and check_out to invoices table
    op.add_column('invoices', sa.Column('check_in', sa.Date(), nullable=True))
    op.add_column('invoices', sa.Column('check_out', sa.Date(), nullable=True))


def downgrade() -> None:
    """Remove check_in and check_out date columns from quotes and invoices"""
    
    # Remove columns from invoices table
    op.drop_column('invoices', 'check_out')
    op.drop_column('invoices', 'check_in')
    
    # Remove columns from quotes table
    op.drop_column('quotes', 'check_out')
    op.drop_column('quotes', 'check_in')