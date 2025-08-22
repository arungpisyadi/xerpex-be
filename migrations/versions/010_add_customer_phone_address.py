"""Add phone_number and address fields to customers table

Revision ID: 010
Revises: 009
Create Date: 2025-08-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add phone_number and address columns to customers table"""
    # Add phone_number column (String(20), nullable)
    op.add_column('customers', sa.Column('phone_number', sa.String(length=20), nullable=True))
    
    # Add address column (Text, nullable)
    op.add_column('customers', sa.Column('address', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove phone_number and address columns from customers table"""
    # Drop columns in reverse order
    op.drop_column('customers', 'address')
    op.drop_column('customers', 'phone_number')