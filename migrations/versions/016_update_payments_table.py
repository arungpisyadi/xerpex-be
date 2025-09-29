"""Update payments table - fix field names and add missing columns

Revision ID: 016
Revises: 015
Create Date: 2025-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_update_payments_table'
down_revision: Union[str, None] = '015_create_survey_jobs_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade the payments table to match the current model"""
    connection = op.get_bind()
    
    def column_exists(table_name, column_name):
        try:
            result = connection.execute(sa.text("""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = :table_name
                AND column_name = :column_name
                AND table_schema = DATABASE()
            """), {"table_name": table_name, "column_name": column_name})
            return result.scalar() > 0
        except:
            # Fallback for SQLite or other databases
            try:
                connection.execute(sa.text(f"SELECT {column_name} FROM {table_name} LIMIT 0"))
                return True
            except:
                return False
    
    # Step 1: Rename payment_mode back to payment_method (if payment_mode exists)
    if column_exists('payments', 'payment_mode'):
        op.alter_column('payments', 'payment_mode', existing_type=sa.String(length=50), new_column_name='payment_method')
    
    # Step 2: Add status column if it doesn't exist
    if not column_exists('payments', 'status'):
        op.add_column('payments', sa.Column('status', sa.String(length=20), nullable=False, default='pending'))
    
    # Step 3: Add notes column if it doesn't exist
    if not column_exists('payments', 'notes'):
        op.add_column('payments', sa.Column('notes', sa.Text(), nullable=True))
    
    # Step 4: Add check constraint for status
    try:
        op.create_check_constraint(
            'check_payment_status',
            'payments',
            "status IN ('pending', 'completed', 'failed', 'refunded')"
        )
    except:
        pass  # Constraint might already exist


def downgrade() -> None:
    """Downgrade the payments table"""
    # Remove check constraint
    try:
        op.drop_constraint('check_payment_status', 'payments', type_='check')
    except:
        pass
    
    # Remove added columns
    try:
        op.drop_column('payments', 'notes')
    except:
        pass
    
    try:
        op.drop_column('payments', 'status')
    except:
        pass
    
    # Rename payment_method back to payment_mode
    try:
        op.alter_column('payments', 'payment_method', existing_type=sa.String(length=50), new_column_name='payment_mode')
    except:
        pass