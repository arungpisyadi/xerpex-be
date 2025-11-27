"""Fix booking_id nullable constraint

Revision ID: 024_fix_booking_id_nullable
Revises: c5f6a7b8d9e0
Create Date: 2025-11-27

This migration fixes the booking_id nullable constraint in the payments table.
The column was created as nullable in migration 022, but MySQL may have changed
it to NOT NULL when the foreign key constraint with CASCADE was added.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7g8h9i0j1k2'
down_revision: Union[str, None] = 'c5f6a7b8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Alter booking_id column to allow NULL values"""
    connection = op.get_bind()
    
    def column_exists(table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
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
    
    # Only alter if the column exists
    if column_exists('payments', 'booking_id'):
        # Alter booking_id to allow NULL values
        # This fixes the issue where MySQL might have created it as NOT NULL
        # when the foreign key constraint was added with ondelete='CASCADE'
        op.alter_column('payments', 'booking_id',
                       existing_type=sa.Integer(),
                       nullable=True)


def downgrade() -> None:
    """Revert booking_id to NOT NULL (may fail if NULL values exist)"""
    connection = op.get_bind()
    
    def column_exists(table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
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
            try:
                connection.execute(sa.text(f"SELECT {column_name} FROM {table_name} LIMIT 0"))
                return True
            except:
                return False
    
    # Only alter if the column exists
    if column_exists('payments', 'booking_id'):
        # Note: This may fail if there are NULL values in booking_id
        # In that case, you would need to update those records first
        op.alter_column('payments', 'booking_id',
                       existing_type=sa.Integer(),
                       nullable=False)