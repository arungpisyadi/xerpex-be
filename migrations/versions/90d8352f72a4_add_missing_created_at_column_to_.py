"""Add missing created_at column to payments table

Revision ID: 90d8352f72a4
Revises: 008
Create Date: 2025-08-22 05:44:04.498451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90d8352f72a4'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if created_at column already exists in payments table
    connection = op.get_bind()
    
    def column_exists(table_name, column_name):
        result = connection.execute(sa.text("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND column_name = :column_name
            AND table_schema = DATABASE()
        """), {"table_name": table_name, "column_name": column_name})
        return result.scalar() > 0
    
    # Add created_at column to payments table if it doesn't exist
    if not column_exists('payments', 'created_at'):
        op.add_column('payments', sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()))
        
        # Set created_at to current timestamp for existing records
        op.execute("UPDATE payments SET created_at = COALESCE(updated_at, NOW()) WHERE created_at IS NULL")
        
        # Make created_at non-nullable
        op.alter_column('payments', 'created_at', existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    # Remove created_at column from payments table
    op.drop_column('payments', 'created_at')