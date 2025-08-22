"""add_status_column_to_customers

Revision ID: 44f7b21741a9
Revises: 1d08e338dae6
Create Date: 2025-08-22 17:54:25.918499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44f7b21741a9'
down_revision: Union[str, None] = '1d08e338dae6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status column to customers table"""
    # Add status column with TINYINT type and default value of 1
    op.add_column('customers', sa.Column('status', sa.SMALLINT(), nullable=False, server_default='1'))


def downgrade() -> None:
    """Remove status column from customers table"""
    # Drop the status column
    op.drop_column('customers', 'status')