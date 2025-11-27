"""Refactor payments module - restructure payments table

Revision ID: 022
Revises: 021
Create Date: 2025-11-26

This migration refactors the payments table to support booking-based payments:
- Drops user_id column (replaced by created_by)
- Adds booking_id column (nullable, FK to bookings)
- Adds payment_type column (down-payment, installment, paid-off)
- Adds created_by column (FK to users)
- Updates status constraint (partial, full)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '022_refactor_payments_module'
down_revision: Union[str, None] = 'q2r3s4t5u6v7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade payments table for booking-based payments"""
    connection = op.get_bind()
    
    # Helper functions
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
            # For MySQL/PostgreSQL check constraints
            result = connection.execute(sa.text("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_name = :constraint_name
                AND table_name = :table_name
                AND table_schema = DATABASE()
            """), {"constraint_name": constraint_name, "table_name": table_name})
            return result.scalar() > 0
        except:
            return False
    
    # Step 1: Add created_by column (nullable first for data migration)
    if not column_exists('payments', 'created_by'):
        op.add_column('payments', sa.Column('created_by', sa.Integer(), nullable=True))
    
    # Step 2: Migrate user_id data to created_by
    if column_exists('payments', 'user_id') and column_exists('payments', 'created_by'):
        op.execute("UPDATE payments SET created_by = user_id WHERE created_by IS NULL")
    
    # Step 3: Add payment_type column (nullable first for data migration)
    if not column_exists('payments', 'payment_type'):
        op.add_column('payments', sa.Column('payment_type', sa.String(length=50), nullable=True))
    
    # Step 4: Set default payment_type for existing records
    if column_exists('payments', 'payment_type'):
        op.execute("UPDATE payments SET payment_type = 'paid-off' WHERE payment_type IS NULL")
    
    # Step 5: Add booking_id column (nullable - linking payments to bookings)
    if not column_exists('payments', 'booking_id'):
        op.add_column('payments', sa.Column('booking_id', sa.Integer(), nullable=True))
    
    # Step 6: Try to migrate booking_id from invoices if possible
    if column_exists('payments', 'booking_id') and column_exists('payments', 'invoice_id'):
        try:
            op.execute("""
                UPDATE payments p
                INNER JOIN invoices i ON p.invoice_id = i.id
                SET p.booking_id = i.booking_id
                WHERE p.booking_id IS NULL AND i.booking_id IS NOT NULL
            """)
        except:
            # If the above doesn't work (e.g., SQLite), try this approach
            pass
    
    # Step 7: Drop old user_id foreign key constraint
    if constraint_exists('fk_payments_user_id', 'payments'):
        try:
            op.drop_constraint('fk_payments_user_id', 'payments', type_='foreignkey')
        except:
            pass
    elif constraint_exists('payments_user_id_fkey', 'payments'):
        try:
            op.drop_constraint('payments_user_id_fkey', 'payments', type_='foreignkey')
        except:
            pass
    
    # Step 8: Drop user_id column
    if column_exists('payments', 'user_id'):
        try:
            op.drop_column('payments', 'user_id')
        except:
            pass
    
    # Step 8.5: Drop any auto-created foreign key constraints that MySQL might have added
    # MySQL might auto-create FK constraints when we add columns, especially for created_by
    # This must happen BEFORE we make columns NOT NULL to avoid conflicts with CASCADE behavior
    inspector = sa.inspect(connection)
    try:
        existing_fks = inspector.get_foreign_keys('payments')
        fk_names = [fk['name'] for fk in existing_fks if fk['name']]
        
        # Drop any auto-created FK constraints (payments_ibfk_1, payments_ibfk_2, etc.)
        # These are typically created by MySQL when column names suggest foreign keys
        for fk_name in fk_names:
            if fk_name and fk_name.startswith('payments_ibfk_'):
                try:
                    op.drop_constraint(fk_name, 'payments', type_='foreignkey')
                except Exception as e:
                    # Constraint might not exist or already be dropped
                    pass
    except Exception as e:
        # SQLite or other databases might not support inspection
        # This is okay - we'll proceed without dropping auto-created constraints
        pass
    
    # Step 9: Make created_by and payment_type non-nullable FIRST (BEFORE foreign keys)
    # This is critical - MySQL needs to know the column is NOT NULL before adding FK with CASCADE
    if column_exists('payments', 'created_by'):
        op.alter_column('payments', 'created_by',
                       existing_type=sa.Integer(),
                       nullable=False)
    
    if column_exists('payments', 'payment_type'):
        op.alter_column('payments', 'payment_type',
                       existing_type=sa.String(length=50),
                       nullable=False)
    
    # Step 10: Add foreign key constraint for created_by (AFTER making NOT NULL)
    if column_exists('payments', 'created_by'):
        try:
            op.create_foreign_key('fk_payments_created_by', 'payments', 'users',
                                ['created_by'], ['id'], ondelete='CASCADE')
        except:
            pass  # Constraint might already exist
    
    # Step 11: Add foreign key constraint for booking_id
    if column_exists('payments', 'booking_id'):
        try:
            op.create_foreign_key('fk_payments_booking_id', 'payments', 'bookings',
                                ['booking_id'], ['id'], ondelete='CASCADE')
        except:
            pass  # Constraint might already exist
    
    # Step 12: Update status check constraint
    # Drop old check constraint
    if constraint_exists('check_payment_status', 'payments'):
        try:
            op.drop_constraint('check_payment_status', 'payments', type_='check')
        except:
            pass
    
    # Create new check constraint with updated values
    try:
        op.create_check_constraint(
            'check_payment_status',
            'payments',
            "status IN ('pending', 'completed', 'failed', 'refunded', 'partial', 'full')"
        )
    except:
        pass  # Constraint might already exist
    
    # Step 13: Create indexes for better query performance
    try:
        op.create_index('ix_payments_created_by', 'payments', ['created_by'])
    except:
        pass
    
    try:
        op.create_index('ix_payments_booking_id', 'payments', ['booking_id'])
    except:
        pass
    
    try:
        op.create_index('ix_payments_payment_type', 'payments', ['payment_type'])
    except:
        pass


def downgrade() -> None:
    """Downgrade payments table to previous structure"""
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
    
    # Step 1: Drop indexes
    try:
        op.drop_index('ix_payments_payment_type', 'payments')
    except:
        pass
    
    try:
        op.drop_index('ix_payments_booking_id', 'payments')
    except:
        pass
    
    try:
        op.drop_index('ix_payments_created_by', 'payments')
    except:
        pass
    
    # Step 2: Drop new check constraint
    try:
        op.drop_constraint('check_payment_status', 'payments', type_='check')
    except:
        pass
    
    # Step 3: Recreate old check constraint
    try:
        op.create_check_constraint(
            'check_payment_status',
            'payments',
            "status IN ('pending', 'completed', 'failed', 'refunded')"
        )
    except:
        pass
    
    # Step 4: Add user_id column back (nullable first)
    if not column_exists('payments', 'user_id'):
        op.add_column('payments', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Step 5: Migrate created_by data back to user_id
    if column_exists('payments', 'created_by') and column_exists('payments', 'user_id'):
        op.execute("UPDATE payments SET user_id = created_by WHERE user_id IS NULL")
    
    # Step 6: Make user_id non-nullable FIRST (BEFORE foreign key)
    # This is critical - MySQL needs to know the column is NOT NULL before adding FK with CASCADE
    if column_exists('payments', 'user_id'):
        op.alter_column('payments', 'user_id',
                       existing_type=sa.Integer(),
                       nullable=False)
    
    # Step 7: Add user_id foreign key constraint back (AFTER making NOT NULL)
    if column_exists('payments', 'user_id'):
        try:
            op.create_foreign_key('fk_payments_user_id', 'payments', 'users',
                                ['user_id'], ['id'], ondelete='CASCADE')
        except:
            pass
    
    # Step 8: Drop foreign key constraints for new columns
    try:
        op.drop_constraint('fk_payments_booking_id', 'payments', type_='foreignkey')
    except:
        pass
    
    try:
        op.drop_constraint('fk_payments_created_by', 'payments', type_='foreignkey')
    except:
        pass
    
    # Step 9: Drop new columns
    if column_exists('payments', 'booking_id'):
        try:
            op.drop_column('payments', 'booking_id')
        except:
            pass
    
    if column_exists('payments', 'payment_type'):
        try:
            op.drop_column('payments', 'payment_type')
        except:
            pass
    
    if column_exists('payments', 'created_by'):
        try:
            op.drop_column('payments', 'created_by')
        except:
            pass