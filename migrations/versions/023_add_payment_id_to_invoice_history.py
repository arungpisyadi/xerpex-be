"""Add payment_id to invoice_history table for payment tracking

Revision ID: 023
Revises: 022
Create Date: 2025-01-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c5f6a7b8d9e0'
down_revision: Union[str, None] = '022_refactor_payments_module'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add payment_id column to invoice_history table"""
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
    
    def constraint_exists(constraint_name: str, table_name: str) -> bool:
        """Check if a constraint exists"""
        inspector = sa.inspect(connection)
        try:
            # Check foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if any(fk['name'] == constraint_name for fk in fks):
                return True
            return False
        except:
            return False
    
    def index_exists(index_name: str, table_name: str) -> bool:
        """Check if an index exists"""
        inspector = sa.inspect(connection)
        try:
            indexes = inspector.get_indexes(table_name)
            return any(idx['name'] == index_name for idx in indexes)
        except:
            return False
    
    # Add payment_id column if it doesn't exist
    if not column_exists('invoice_history', 'payment_id'):
        op.add_column(
            'invoice_history',
            sa.Column('payment_id', sa.Integer(), nullable=True)
        )
    
    # Add foreign key constraint if it doesn't exist
    if not constraint_exists('fk_invoice_history_payment_id', 'invoice_history'):
        try:
            op.create_foreign_key(
                'fk_invoice_history_payment_id',
                'invoice_history',
                'payments',
                ['payment_id'],
                ['id'],
                ondelete='CASCADE'
            )
        except:
            pass  # Constraint might already exist
    
    # Add index for performance if it doesn't exist
    if not index_exists('idx_invoice_history_payment_id', 'invoice_history'):
        try:
            op.create_index(
                'idx_invoice_history_payment_id',
                'invoice_history',
                ['payment_id'],
                unique=False
            )
        except:
            pass  # Index might already exist


def downgrade() -> None:
    """Remove payment_id column from invoice_history table"""
    
    # Drop index first
    op.drop_index('idx_invoice_history_payment_id', table_name='invoice_history')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_invoice_history_payment_id', 'invoice_history', type_='foreignkey')
    
    # Drop column
    op.drop_column('invoice_history', 'payment_id')