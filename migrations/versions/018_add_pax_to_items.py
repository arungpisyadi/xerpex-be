"""Add pax column to quote_items and invoice_items tables

Revision ID: 018
Revises: 017
Create Date: 2025-11-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6g7h8i9j0'
down_revision: Union[str, None] = '37b6c7220f62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pax column to quote_items and invoice_items tables"""
    # Add pax column to quote_items table
    # Type: Integer, Default: 1, Not nullable
    op.add_column('quote_items', sa.Column('pax', sa.Integer(), nullable=False, server_default='1'))
    
    # Add pax column to invoice_items table
    # Type: Integer, Default: 1, Not nullable
    op.add_column('invoice_items', sa.Column('pax', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Remove pax column from quote_items and invoice_items tables"""
    # Drop pax column from invoice_items table
    op.drop_column('invoice_items', 'pax')
    
    # Drop pax column from quote_items table
    op.drop_column('quote_items', 'pax')