"""Allow null email in surveys table

Revision ID: 014
Revises: 013
Create Date: 2025-09-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change email column in surveys table to allow NULL values"""
    # Alter the email column to allow NULL values
    op.alter_column(
        'surveys',
        'email',
        existing_type=sa.String(length=100),
        nullable=True
    )


def downgrade() -> None:
    """Change email column in surveys table back to NOT NULL"""
    # First, update any NULL email values to empty string to avoid constraint violation
    op.execute("UPDATE surveys SET email = '' WHERE email IS NULL")
    
    # Alter the email column back to NOT NULL
    op.alter_column(
        'surveys',
        'email',
        existing_type=sa.String(length=100),
        nullable=False
    )