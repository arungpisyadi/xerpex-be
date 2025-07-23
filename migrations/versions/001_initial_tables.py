"""Initial tables

Revision ID: 001
Revises: 
Create Date: 2025-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
        sa.CheckConstraint("role IN ('admin', 'manager', 'staff')")
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create user_activities table
    op.create_table(
        'user_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_activities_id'), 'user_activities', ['id'], unique=False)
    
    # Create villas table
    op.create_table(
        'villas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('room_type', sa.String(length=50), nullable=False),
        sa.Column('base_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_villas_id'), 'villas', ['id'], unique=False)
    
    # Create villa_availability table
    op.create_table(
        'villa_availability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('villa_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=True, default=True),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('villa_id', 'date')
    )
    op.create_index(op.f('ix_villa_availability_id'), 'villa_availability', ['id'], unique=False)
    
    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_code', sa.String(length=20), nullable=False),
        sa.Column('guest_name', sa.String(length=100), nullable=False),
        sa.Column('guest_email', sa.String(length=100), nullable=True),
        sa.Column('guest_phone', sa.String(length=20), nullable=True),
        sa.Column('check_in', sa.Date(), nullable=False),
        sa.Column('check_out', sa.Date(), nullable=False),
        sa.Column('total_pax', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_code'),
        sa.CheckConstraint("status IN ('pending', 'confirmed', 'ongoing', 'completed', 'cancelled')")
    )
    op.create_index(op.f('ix_bookings_id'), 'bookings', ['id'], unique=False)
    op.create_index(op.f('ix_bookings_booking_code'), 'bookings', ['booking_code'], unique=True)
    
    # Create booking_villas table
    op.create_table(
        'booking_villas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('villa_id', sa.Integer(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_villas_id'), 'booking_villas', ['id'], unique=False)
    
    # Create booking_packages table
    op.create_table(
        'booking_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('package_name', sa.String(length=100), nullable=False),
        sa.Column('package_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_packages_id'), 'booking_packages', ['id'], unique=False)
    
    # Create booking_addons table
    op.create_table(
        'booking_addons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('service_name', sa.String(length=100), nullable=False),
        sa.Column('service_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=True, default=1),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_booking_addons_id'), 'booking_addons', ['id'], unique=False)
    
    # Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('payment_method', sa.String(length=50), nullable=False),
        sa.Column('payment_date', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'paid', 'failed', 'refunded')")
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
        sa.CheckConstraint("status IN ('unpaid', 'paid', 'overdue')")
    )
    op.create_index(op.f('ix_invoices_id'), 'invoices', ['id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=True)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('invoices')
    op.drop_table('payments')
    op.drop_table('booking_addons')
    op.drop_table('booking_packages')
    op.drop_table('booking_villas')
    op.drop_table('bookings')
    op.drop_table('villa_availability')
    op.drop_table('villas')
    op.drop_table('user_activities')
    op.drop_table('users')