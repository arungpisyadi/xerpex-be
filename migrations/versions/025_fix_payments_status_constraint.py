"""Remove payments status check constraint

Removes the database-level status validation check constraint from the payments table.
Status validation is now handled exclusively at the application level via Pydantic schemas,
which provides better flexibility for adding new status values without database migrations.

Revision ID: 025_fix_payments_status_constraint
Revises: 024_fix_booking_id_nullable
Create Date: 2025-11-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'l3m4n5o6p7q8'
down_revision: Union[str, None] = 'f7g8h9i0j1k2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the status check constraint - rely on application-level validation"""
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    try:
        # Find and drop any status-related check constraints
        constraints = inspector.get_check_constraints('payments')
        for constraint in constraints:
            constraint_text = constraint.get('sqltext', '')
            if 'status' in constraint_text.lower():
                op.drop_constraint(constraint['name'], 'payments', type_='check')
                print(f"Dropped status constraint: {constraint['name']}")
                break
    except Exception as e:
        # Constraint might not exist or already dropped
        print(f"Could not drop status constraint: {e}")
        pass


def downgrade() -> None:
    """Recreate the original status check constraint"""
    op.create_check_constraint(
        'payments_chk_1',
        'payments',
        "status IN ('pending', 'completed', 'failed', 'refunded')"
    )