"""Add phone field to users table

Revision ID: 013
Revises: 012
Create Date: 2025-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add phone column to users table"""
    # Add phone column (String(20), nullable)
    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Remove phone column from users table"""
    # Drop the phone column
    op.drop_column('users', 'phone')