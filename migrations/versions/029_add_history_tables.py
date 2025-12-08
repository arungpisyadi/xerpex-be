"""Add history tracking tables for quotes, payments, and bookings

Revision ID: 029
Revises: b2c3d4e5f6g7
Create Date: 2025-12-08

This migration adds comprehensive history tracking:
1. Creates quote_history table for quote lifecycle tracking
2. Creates payment_history table for payment lifecycle tracking
3. Modifies booking_history table to add payment_id reference
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '029'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add history tracking tables for quotes, payments, and modify booking_history"""
    
    # ========================================
    # 1. Create quote_history table
    # ========================================
    op.create_table(
        'quote_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ['quote_id'], 
            ['quotes.id'], 
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], 
            ['users.id'], 
            ondelete='CASCADE'
        ),
        
        # Check constraint for event_category
        sa.CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'data')",
            name='check_quote_history_event_category'
        ),
        
        # SQLite compatibility
        {"sqlite_autoincrement": True}
    )
    
    # Create indexes for quote_history
    op.create_index('ix_quote_history_id', 'quote_history', ['id'], unique=False)
    op.create_index('idx_quote_history_quote_id', 'quote_history', ['quote_id'], unique=False)
    op.create_index('idx_quote_history_user_id', 'quote_history', ['user_id'], unique=False)
    op.create_index('idx_quote_history_created_at', 'quote_history', ['created_at'], unique=False)
    
    # ========================================
    # 2. Create payment_history table
    # ========================================
    op.create_table(
        'payment_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('payment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.current_timestamp()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ['payment_id'], 
            ['payments.id'], 
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], 
            ['users.id'], 
            ondelete='CASCADE'
        ),
        
        # Check constraint for event_category
        sa.CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'data')",
            name='check_payment_history_event_category'
        ),
        
        # SQLite compatibility
        {"sqlite_autoincrement": True}
    )
    
    # Create indexes for payment_history
    op.create_index('ix_payment_history_id', 'payment_history', ['id'], unique=False)
    op.create_index('idx_payment_history_payment_id', 'payment_history', ['payment_id'], unique=False)
    op.create_index('idx_payment_history_user_id', 'payment_history', ['user_id'], unique=False)
    op.create_index('idx_payment_history_created_at', 'payment_history', ['created_at'], unique=False)
    
    # ========================================
    # 3. Modify booking_history table
    # ========================================
    # Add payment_id column to booking_history
    op.add_column(
        'booking_history',
        sa.Column('payment_id', sa.Integer(), nullable=True)
    )
    
    # Add foreign key constraint for payment_id
    op.create_foreign_key(
        'fk_booking_history_payment_id',
        'booking_history',
        'payments',
        ['payment_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add index on payment_id
    op.create_index('idx_booking_history_payment_id', 'booking_history', ['payment_id'], unique=False)


def downgrade() -> None:
    """Remove history tracking tables and modifications"""
    
    # ========================================
    # 1. Remove modifications to booking_history
    # ========================================
    # Drop index first
    op.drop_index('idx_booking_history_payment_id', table_name='booking_history')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_booking_history_payment_id', 'booking_history', type_='foreignkey')
    
    # Drop column
    op.drop_column('booking_history', 'payment_id')
    
    # ========================================
    # 2. Drop payment_history table
    # ========================================
    # Drop indexes first
    op.drop_index('idx_payment_history_created_at', table_name='payment_history')
    op.drop_index('idx_payment_history_user_id', table_name='payment_history')
    op.drop_index('idx_payment_history_payment_id', table_name='payment_history')
    op.drop_index('ix_payment_history_id', table_name='payment_history')
    
    # Drop table
    op.drop_table('payment_history')
    
    # ========================================
    # 3. Drop quote_history table
    # ========================================
    # Drop indexes first
    op.drop_index('idx_quote_history_created_at', table_name='quote_history')
    op.drop_index('idx_quote_history_user_id', table_name='quote_history')
    op.drop_index('idx_quote_history_quote_id', table_name='quote_history')
    op.drop_index('ix_quote_history_id', table_name='quote_history')
    
    # Drop table
    op.drop_table('quote_history')