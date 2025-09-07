"""add_month_validation_check_constraint

Revision ID: a4ddf13895b3
Revises: 8b715eca4f70
Create Date: 2025-09-07 22:22:17.052872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4ddf13895b3'
down_revision: Union[str, None] = '8b715eca4f70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add check constraint to ensure month is between 1 and 12
    op.create_check_constraint(
        'month_range_check',
        'sales_targets',
        'month >= 1 AND month <= 12'
    )


def downgrade() -> None:
    # Drop the check constraint
    op.drop_constraint('month_range_check', 'sales_targets', type_='check')