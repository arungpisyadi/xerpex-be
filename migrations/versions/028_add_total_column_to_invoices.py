"""Add total column to invoices table and migrate data from amount_due

Revision ID: 028
Revises: 027
Create Date: 2025-12-11

This migration refactors the invoice schema to properly represent the total
invoice amount. The 'total' column will store the complete invoice amount
(previously stored in 'amount_due'), and 'amount_due' will be recalculated
as 'total - amount_paid' whenever payments are made.

Migration steps:
1. Add total column (nullable first to allow data migration)
2. Copy all existing amount_due values to the new total column
3. Make total column NOT NULL after data is migrated
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add total column to invoices and migrate data from amount_due"""
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
    
    # Step 1: Add total column if it doesn't exist (nullable first for data migration)
    if not column_exists('invoices', 'total'):
        print("Adding total column to invoices table...")
        op.add_column('invoices', sa.Column('total', DECIMAL(15, 2), nullable=True))
    else:
        print("Total column already exists in invoices table, skipping creation...")
    
    # Step 2: Copy all existing amount_due values to total column
    # This ensures all existing data is preserved in the new column
    print("Migrating data from amount_due to total column...")
    connection.execute(sa.text("""
        UPDATE invoices 
        SET total = amount_due 
        WHERE total IS NULL OR total = 0
    """))
    
    # Step 3: Make total column NOT NULL after data is migrated
    # Set default value of 0.00 for any remaining NULL values (edge case handling)
    print("Setting default values for any NULL total values...")
    connection.execute(sa.text("""
        UPDATE invoices 
        SET total = 0.00 
        WHERE total IS NULL
    """))
    
    # Step 4: Alter column to be NOT NULL
    print("Making total column NOT NULL...")
    op.alter_column('invoices', 'total',
                   existing_type=DECIMAL(15, 2),
                   nullable=False)
    
    print("Migration completed successfully!")


def downgrade() -> None:
    """Remove the total column from invoices table"""
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
    
    # Drop the total column if it exists
    if column_exists('invoices', 'total'):
        print("Dropping total column from invoices table...")
        op.drop_column('invoices', 'total')
    else:
        print("Total column doesn't exist in invoices table, skipping drop...")
    
    print("Downgrade completed successfully!")