"""Restructure invoices and payments tables for invoicing system

Revision ID: 008
Revises: 007
Create Date: 2025-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, backup existing invoice data if needed
    # Note: In production, you'd want to create a backup table first
    
    # Drop existing invoice_items table if it exists (from old structure)
    try:
        op.drop_table('invoice_items')
    except:
        pass  # Table might not exist
    
    # Check which columns already exist in invoices table
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
    
    # Add new columns to invoices table (only if they don't exist)
    if not column_exists('invoices', 'user_id'):
        op.add_column('invoices', sa.Column('user_id', sa.Integer(), nullable=True))
    if not column_exists('invoices', 'customer_id'):
        op.add_column('invoices', sa.Column('customer_id', sa.Integer(), nullable=True))
    if not column_exists('invoices', 'quote_id'):
        op.add_column('invoices', sa.Column('quote_id', sa.Integer(), nullable=True))
    if not column_exists('invoices', 'issue_date'):
        op.add_column('invoices', sa.Column('issue_date', sa.Date(), nullable=True, default=sa.func.current_date()))
    if not column_exists('invoices', 'payment_terms'):
        op.add_column('invoices', sa.Column('payment_terms', sa.String(length=50), nullable=True))
    if not column_exists('invoices', 'amount_due'):
        op.add_column('invoices', sa.Column('amount_due', sa.Numeric(precision=10, scale=2), nullable=True, default=0.00))
    if not column_exists('invoices', 'tax_total'):
        op.add_column('invoices', sa.Column('tax_total', sa.Numeric(precision=10, scale=2), nullable=True, default=0.00))
    if not column_exists('invoices', 'amount_paid'):
        op.add_column('invoices', sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=True, default=0.00))
    if not column_exists('invoices', 'updated_at'):
        op.add_column('invoices', sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()))
    
    # Rename total_amount to total (check if column exists first)
    if column_exists('invoices', 'total_amount'):
        op.alter_column('invoices', 'total_amount', existing_type=sa.Numeric(precision=10, scale=2), new_column_name='total')
    
    # Set default values for existing records
    op.execute("UPDATE invoices SET user_id = 1 WHERE user_id IS NULL")  # Assuming admin user exists
    op.execute("UPDATE invoices SET issue_date = created_at WHERE issue_date IS NULL")
    op.execute("UPDATE invoices SET amount_due = total WHERE amount_due IS NULL")
    
    # Make required columns non-nullable
    op.alter_column('invoices', 'user_id', existing_type=sa.Integer(), nullable=False)
    op.alter_column('invoices', 'issue_date', existing_type=sa.Date(), nullable=False)
    op.alter_column('invoices', 'amount_due', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
    op.alter_column('invoices', 'tax_total', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
    op.alter_column('invoices', 'amount_paid', existing_type=sa.Numeric(precision=10, scale=2), nullable=False)
    
    # Add foreign key constraints (only if they don't exist)
    try:
        op.create_foreign_key('fk_invoices_user_id', 'invoices', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    except:
        pass  # Foreign key might already exist
    try:
        op.create_foreign_key('fk_invoices_customer_id', 'invoices', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')
    except:
        pass  # Foreign key might already exist
    try:
        op.create_foreign_key('fk_invoices_quote_id', 'invoices', 'quotes', ['quote_id'], ['id'], ondelete='SET NULL')
    except:
        pass  # Foreign key might already exist
    
    # Update invoice status constraint (only if it exists)
    try:
        op.drop_constraint('invoices_status_check', 'invoices', type_='check')
    except:
        pass  # Constraint might not exist
    
    # Create new check constraint
    try:
        op.create_check_constraint(
            'check_invoice_status',
            'invoices',
            "status IN ('draft', 'sent', 'partially_paid', 'paid', 'overdue', 'cancelled')"
        )
    except:
        pass  # Constraint might already exist
    
    # Create new invoice_items table
    op.create_table(
        'invoice_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_items_id'), 'invoice_items', ['id'], unique=False)
    
    # Update payments table (only add columns if they don't exist)
    if not column_exists('payments', 'user_id'):
        op.add_column('payments', sa.Column('user_id', sa.Integer(), nullable=True))
    if not column_exists('payments', 'invoice_id'):
        op.add_column('payments', sa.Column('invoice_id', sa.Integer(), nullable=True))
    if not column_exists('payments', 'reference_number'):
        op.add_column('payments', sa.Column('reference_number', sa.String(length=50), nullable=True))
    if not column_exists('payments', 'updated_at'):
        op.add_column('payments', sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()))
    
    # Rename columns in payments (check if columns exist first)
    if column_exists('payments', 'recorded_by'):
        op.alter_column('payments', 'recorded_by', existing_type=sa.Integer(), new_column_name='created_by')
    if column_exists('payments', 'payment_method'):
        op.alter_column('payments', 'payment_method', existing_type=sa.String(length=50), new_column_name='payment_mode')
    # Convert payment_date from DateTime to Date
    op.alter_column('payments', 'payment_date', existing_type=sa.DateTime(), type_=sa.Date())
    
    # Set default values for existing payments
    op.execute("UPDATE payments SET user_id = 1 WHERE user_id IS NULL")
    
    # Make user_id non-nullable
    op.alter_column('payments', 'user_id', existing_type=sa.Integer(), nullable=False)
    
    # Add foreign key constraints for payments (only if they don't exist)
    try:
        op.create_foreign_key('fk_payments_user_id', 'payments', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    except:
        pass  # Foreign key might already exist
    try:
        op.create_foreign_key('fk_payments_invoice_id', 'payments', 'invoices', ['invoice_id'], ['id'], ondelete='CASCADE')
    except:
        pass  # Foreign key might already exist
    
    # Remove old booking_id foreign key from payments (if we're moving away from booking-based payments)
    # op.drop_constraint('payments_booking_id_fkey', 'payments', type_='foreignkey')
    # op.drop_column('payments', 'booking_id')


def downgrade() -> None:
    # This is a complex migration, downgrade would need careful consideration
    # For now, we'll implement basic rollback
    
    # Drop new tables
    op.drop_table('invoice_items')
    
    # Remove added columns from invoices
    op.drop_constraint('fk_invoices_user_id', 'invoices', type_='foreignkey')
    op.drop_constraint('fk_invoices_customer_id', 'invoices', type_='foreignkey')
    op.drop_constraint('fk_invoices_quote_id', 'invoices', type_='foreignkey')
    
    op.drop_column('invoices', 'user_id')
    op.drop_column('invoices', 'customer_id')
    op.drop_column('invoices', 'quote_id')
    op.drop_column('invoices', 'issue_date')
    op.drop_column('invoices', 'payment_terms')
    op.drop_column('invoices', 'amount_due')
    op.drop_column('invoices', 'tax_total')
    op.drop_column('invoices', 'amount_paid')
    op.drop_column('invoices', 'updated_at')
    
    # Rename total back to total_amount
    op.alter_column('invoices', 'total', new_column_name='total_amount')
    
    # Remove added columns from payments
    op.drop_constraint('fk_payments_user_id', 'payments', type_='foreignkey')
    op.drop_constraint('fk_payments_invoice_id', 'payments', type_='foreignkey')
    
    op.drop_column('payments', 'user_id')
    op.drop_column('payments', 'invoice_id')
    op.drop_column('payments', 'reference_number')
    op.drop_column('payments', 'updated_at')
    
    # Rename columns back
    op.alter_column('payments', 'created_by', new_column_name='recorded_by')
    op.alter_column('payments', 'payment_mode', new_column_name='payment_method')
    op.alter_column('payments', 'payment_date', type_=sa.DateTime())