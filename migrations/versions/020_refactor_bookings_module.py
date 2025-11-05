"""Refactor bookings module to align with quotes architecture

Revision ID: 020
Revises: 019
Create Date: 2025-11-03

This migration refactors the bookings module to align with the quotes module structure:
- Drops booking_packages and booking_addons tables
- Creates booking_items table for flexible line items
- Creates booking_history table for audit trail
- Updates bookings table with customer_id, user_id, and financial fields
- Updates booking_villas table with rate and calculation fields
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mysql import DECIMAL


# revision identifiers, used by Alembic.
revision: str = 'p1q2r3s4t5u6'
down_revision: Union[str, None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema for bookings refactor"""
    
    # Helper function to check if column exists
    def column_exists(table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table"""
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    
    # Helper function to check if table exists
    def table_exists(table_name: str) -> bool:
        """Check if a table exists in the database"""
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        return table_name in inspector.get_table_names()
    
    # Step 1: Create booking_items table
    if not table_exists('booking_items'):
        op.create_table(
        'booking_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('pax', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False),
        sa.Column('discount', sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('line_total', sa.Numeric(15, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('pax >= 1', name='check_booking_item_pax'),
        sa.CheckConstraint('unit_price >= 0', name='check_booking_item_unit_price'),
        sa.CheckConstraint('discount >= 0', name='check_booking_item_discount')
        )
        op.create_index('ix_booking_items_id', 'booking_items', ['id'])
        op.create_index('ix_booking_items_booking_id', 'booking_items', ['booking_id'])
        op.create_index('ix_booking_items_package_id', 'booking_items', ['package_id'])
    
    # Step 2: Create booking_history table
    if not table_exists('booking_history'):
        op.create_table(
        'booking_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('field_name', sa.String(100), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('change_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "change_type IN ('created', 'status_change', 'field_update', 'item_added', " +
            "'item_removed', 'villa_added', 'villa_removed', 'payment_received')",
            name='check_booking_history_change_type'
        )
        )
        op.create_index('ix_booking_history_id', 'booking_history', ['id'])
        op.create_index('ix_booking_history_booking_id', 'booking_history', ['booking_id'])
        op.create_index('ix_booking_history_user_id', 'booking_history', ['user_id'])
        op.create_index('ix_booking_history_created_at', 'booking_history', ['created_at'])
    
    # Step 3: Add new columns to bookings table (only if they don't exist)
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        # Check and add user_id if it doesn't exist
        if not column_exists('bookings', 'user_id'):
            batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        
        # Check and add customer_id if it doesn't exist
        if not column_exists('bookings', 'customer_id'):
            batch_op.add_column(sa.Column('customer_id', sa.Integer(), nullable=True))
        
        # Check and add sales_person_id if it doesn't exist
        if not column_exists('bookings', 'sales_person_id'):
            batch_op.add_column(sa.Column('sales_person_id', sa.Integer(), nullable=True))
        
        # Check and add financial columns if they don't exist
        if not column_exists('bookings', 'total'):
            batch_op.add_column(sa.Column('total', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
        
        if not column_exists('bookings', 'tax_total'):
            batch_op.add_column(sa.Column('tax_total', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
        
        if not column_exists('bookings', 'amount_paid'):
            batch_op.add_column(sa.Column('amount_paid', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
        
        if not column_exists('bookings', 'amount_due'):
            batch_op.add_column(sa.Column('amount_due', sa.Numeric(15, 2), nullable=True, server_default='0.00'))
    
    # Step 4: Migrate existing data in bookings table
    # Set user_id to created_by where available, otherwise default to admin user (id=1)
    if column_exists('bookings', 'user_id'):
        op.execute("UPDATE bookings SET user_id = COALESCE(created_by, 1) WHERE user_id IS NULL")
    
    # Create a default customer for existing bookings or try to map by email
    # Note: This assumes a default customer with id=1 exists or will be created
    if column_exists('bookings', 'customer_id'):
        op.execute("""
            UPDATE bookings
            SET customer_id = COALESCE(
                (SELECT id FROM customers WHERE email = bookings.guest_email LIMIT 1),
                1
            )
            WHERE customer_id IS NULL
        """)
    
    # Calculate totals from booking_packages and booking_addons (only if columns exist)
    if column_exists('bookings', 'total'):
        # First, calculate package totals
        op.execute("""
            UPDATE bookings
            SET total = COALESCE(
                (SELECT SUM(package_price) FROM booking_packages WHERE booking_id = bookings.id),
                0
            )
            WHERE total = 0 OR total IS NULL
        """)
        
        # Add addon totals to the total
        op.execute("""
            UPDATE bookings
            SET total = total + COALESCE(
                (SELECT SUM(service_price * quantity) FROM booking_addons WHERE booking_id = bookings.id),
                0
            )
            WHERE EXISTS (SELECT 1 FROM booking_addons WHERE booking_id = bookings.id)
        """)
    
    if column_exists('bookings', 'amount_due') and column_exists('bookings', 'total'):
        # Set amount_due equal to total for existing bookings
        op.execute("UPDATE bookings SET amount_due = total WHERE amount_due = 0 OR amount_due IS NULL")
    
    if column_exists('bookings', 'amount_paid'):
        # Calculate amount_paid from payments table if the payments table exists and has a booking_id column
        # Note: This may need adjustment based on your actual payments table structure
        op.execute("""
            UPDATE bookings
            SET amount_paid = COALESCE(
                (SELECT SUM(amount) FROM payments WHERE booking_id = bookings.id AND status = 'paid'),
                0
            )
            WHERE amount_paid = 0 OR amount_paid IS NULL
        """)
    
    if column_exists('bookings', 'amount_due') and column_exists('bookings', 'total') and column_exists('bookings', 'amount_paid'):
        # Update amount_due to reflect payments
        op.execute("UPDATE bookings SET amount_due = total - amount_paid")
    
    # Step 5: Make nullable columns non-nullable after data migration
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        if column_exists('bookings', 'user_id'):
            batch_op.alter_column('user_id',
                            existing_type=sa.Integer(),
                            nullable=False,
                            existing_nullable=True)
        
        if column_exists('bookings', 'customer_id'):
            batch_op.alter_column('customer_id',
                            existing_type=sa.Integer(),
                            nullable=False,
                            existing_nullable=True)
        
        if column_exists('bookings', 'total'):
            batch_op.alter_column('total',
                            existing_type=sa.Numeric(15, 2),
                            nullable=False,
                            existing_nullable=True)
        
        if column_exists('bookings', 'tax_total'):
            batch_op.alter_column('tax_total',
                            existing_type=sa.Numeric(15, 2),
                            nullable=False,
                            existing_nullable=True)
        
        if column_exists('bookings', 'amount_paid'):
            batch_op.alter_column('amount_paid',
                            existing_type=sa.Numeric(15, 2),
                            nullable=False,
                            existing_nullable=True)
        
        if column_exists('bookings', 'amount_due'):
            batch_op.alter_column('amount_due',
                            existing_type=sa.Numeric(15, 2),
                            nullable=False,
                            existing_nullable=True)
    
    # Step 6: Add foreign key constraints to bookings table (only if columns exist and constraints don't)
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    existing_fks = [fk['name'] for fk in inspector.get_foreign_keys('bookings')]
    
    if column_exists('bookings', 'user_id') and 'fk_bookings_user_id' not in existing_fks:
        op.create_foreign_key('fk_bookings_user_id', 'bookings', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    
    if column_exists('bookings', 'customer_id') and 'fk_bookings_customer_id' not in existing_fks:
        op.create_foreign_key('fk_bookings_customer_id', 'bookings', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')
    
    if column_exists('bookings', 'sales_person_id') and 'fk_bookings_sales_person_id' not in existing_fks:
        op.create_foreign_key('fk_bookings_sales_person_id', 'bookings', 'users', ['sales_person_id'], ['id'], ondelete='SET NULL')
    
    # Step 7: Create indexes for bookings table (only if they don't exist)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('bookings')]
    
    if column_exists('bookings', 'user_id') and 'ix_bookings_user_id' not in existing_indexes:
        op.create_index('ix_bookings_user_id', 'bookings', ['user_id'])
    
    if column_exists('bookings', 'customer_id') and 'ix_bookings_customer_id' not in existing_indexes:
        op.create_index('ix_bookings_customer_id', 'bookings', ['customer_id'])
    
    if 'ix_bookings_booking_code' not in existing_indexes:
        op.create_index('ix_bookings_booking_code', 'bookings', ['booking_code'])
    
    if 'ix_bookings_check_in' not in existing_indexes:
        op.create_index('ix_bookings_check_in', 'bookings', ['check_in'])
    
    if 'ix_bookings_status' not in existing_indexes:
        op.create_index('ix_bookings_status', 'bookings', ['status'])
    
    # Step 8: Update bookings table status constraint
    # Drop old constraint if it exists
    try:
        op.drop_constraint('check_booking_status', 'bookings', type_='check')
    except:
        pass  # Constraint might not exist
    
    # Create updated constraint with new status values
    op.create_check_constraint(
        'check_booking_status',
        'bookings',
        "status IN ('pending', 'confirmed', 'checked_in', 'checked_out', 'completed', 'cancelled')"
    )
    
    # Step 9: Migrate data from booking_packages to booking_items
    if table_exists('booking_packages') and table_exists('booking_items'):
        op.execute("""
            INSERT INTO booking_items (booking_id, package_id, pax, unit_price, discount, line_total, created_at)
            SELECT
                bp.booking_id,
                COALESCE(p.id, 1) as package_id,
                b.total_pax,
                bp.package_price,
                0.00,
                bp.package_price,
                CURRENT_TIMESTAMP
            FROM booking_packages bp
            JOIN bookings b ON bp.booking_id = b.id
            LEFT JOIN packages p ON p.name = bp.package_name
        """)
    
    # Step 10: Migrate data from booking_addons to booking_items
    if table_exists('booking_addons') and table_exists('booking_items'):
        op.execute("""
            INSERT INTO booking_items (booking_id, package_id, pax, unit_price, discount, line_total, created_at)
            SELECT
                ba.booking_id,
                COALESCE(p.id, 1) as package_id,
                ba.quantity,
                ba.service_price,
                0.00,
                ba.service_price * ba.quantity,
                CURRENT_TIMESTAMP
            FROM booking_addons ba
            LEFT JOIN packages p ON p.name = ba.service_name
        """)
    
    # Step 11: booking_villas remains as simple junction table (no additional columns needed)
    # The table already has: id, booking_id, villa_id, created_at
    
    # Step 12: Create initial history records for existing bookings
    if table_exists('booking_history'):
        op.execute("""
            INSERT INTO booking_history (booking_id, user_id, field_name, old_value, new_value, change_type, created_at)
            SELECT
                id,
                user_id,
                'status',
                NULL,
                status,
                'created',
                created_at
            FROM bookings
        """)
    
    # Step 13: Drop redundant guest columns from bookings table
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        if column_exists('bookings', 'guest_name'):
            batch_op.drop_column('guest_name')
        
        if column_exists('bookings', 'guest_email'):
            batch_op.drop_column('guest_email')
        
        if column_exists('bookings', 'guest_phone'):
            batch_op.drop_column('guest_phone')
    
    # Step 14: Drop old tables (booking_packages and booking_addons)
    if table_exists('booking_addons'):
        op.drop_table('booking_addons')
    if table_exists('booking_packages'):
        op.drop_table('booking_packages')


def downgrade() -> None:
    """Downgrade database schema (reverse bookings refactor)"""
    
    # Step 1: Recreate booking_packages table
    op.create_table(
        'booking_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('package_name', sa.String(100), nullable=False),
        sa.Column('package_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Step 2: Recreate booking_addons table
    op.create_table(
        'booking_addons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('service_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True, server_default='1'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Step 3: Re-add guest columns to bookings table
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('guest_name', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('guest_email', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('guest_phone', sa.String(20), nullable=True))
    
    # Step 4: Migrate customer data back to guest fields
    op.execute("""
        UPDATE bookings b
        SET
            guest_name = (SELECT name FROM customers WHERE id = b.customer_id),
            guest_email = (SELECT email FROM customers WHERE id = b.customer_id),
            guest_phone = (SELECT phone FROM customers WHERE id = b.customer_id)
        WHERE customer_id IS NOT NULL
    """)
    
    # Step 5: Migrate data back from booking_items to booking_packages/booking_addons
    # Note: This is a best-effort migration and may lose some data fidelity
    op.execute("""
        INSERT INTO booking_packages (booking_id, package_name, package_price, notes)
        SELECT
            bi.booking_id,
            p.name,
            bi.unit_price,
            NULL
        FROM booking_items bi
        JOIN packages p ON bi.package_id = p.id
    """)
    
    # Step 6: booking_villas remains as simple junction table (no columns to drop)
    
    # Step 7: Drop indexes from bookings table
    op.drop_index('ix_bookings_status', 'bookings')
    op.drop_index('ix_bookings_check_in', 'bookings')
    op.drop_index('ix_bookings_booking_code', 'bookings')
    op.drop_index('ix_bookings_customer_id', 'bookings')
    op.drop_index('ix_bookings_user_id', 'bookings')
    
    # Step 8: Drop foreign key constraints from bookings
    op.drop_constraint('fk_bookings_sales_person_id', 'bookings', type_='foreignkey')
    op.drop_constraint('fk_bookings_customer_id', 'bookings', type_='foreignkey')
    op.drop_constraint('fk_bookings_user_id', 'bookings', type_='foreignkey')
    
    # Step 9: Remove new columns from bookings table
    op.drop_column('bookings', 'amount_due')
    op.drop_column('bookings', 'amount_paid')
    op.drop_column('bookings', 'tax_total')
    op.drop_column('bookings', 'total')
    op.drop_column('bookings', 'sales_person_id')
    op.drop_column('bookings', 'customer_id')
    op.drop_column('bookings', 'user_id')
    
    # Step 10: Drop status constraint and recreate old one
    op.drop_constraint('check_booking_status', 'bookings', type_='check')
    
    # Step 11: Drop booking_history table
    op.drop_index('ix_booking_history_created_at', 'booking_history')
    op.drop_index('ix_booking_history_user_id', 'booking_history')
    op.drop_index('ix_booking_history_booking_id', 'booking_history')
    op.drop_index('ix_booking_history_id', 'booking_history')
    op.drop_table('booking_history')
    
    # Step 12: Drop booking_items table
    op.drop_index('ix_booking_items_package_id', 'booking_items')
    op.drop_index('ix_booking_items_booking_id', 'booking_items')
    op.drop_index('ix_booking_items_id', 'booking_items')
    op.drop_table('booking_items')