"""Add invoice history table for audit trail

Revision ID: 011
Revises: 010
Create Date: 2025-01-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add invoice_history table for tracking invoice lifecycle events"""
    
    # Create invoice_history table
    op.create_table(
        'invoice_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_category', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.current_timestamp()),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign key constraints
        sa.ForeignKeyConstraint(
            ['invoice_id'], 
            ['invoices.id'], 
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], 
            ['users.id'], 
            ondelete='CASCADE'
        ),
        
        # Check constraint for event_category
        sa.CheckConstraint(
            "event_category IN ('lifecycle', 'status', 'workflow', 'payment')",
            name='check_invoice_history_event_category'
        ),
        
        # SQLite compatibility
        {"sqlite_autoincrement": True}
    )
    
    # Create indexes for performance
    op.create_index('ix_invoice_history_id', 'invoice_history', ['id'], unique=False)
    op.create_index('idx_invoice_history_invoice_id', 'invoice_history', ['invoice_id'], unique=False)
    op.create_index('idx_invoice_history_created_at_desc', 'invoice_history', ['created_at'], unique=False)
    op.create_index('idx_invoice_history_event_category', 'invoice_history', ['event_category'], unique=False)
    op.create_index('idx_invoice_history_composite', 'invoice_history', ['invoice_id', 'created_at', 'event_category'], unique=False)


def downgrade() -> None:
    """Drop invoice_history table"""
    
    # Drop indexes first
    op.drop_index('idx_invoice_history_composite', table_name='invoice_history')
    op.drop_index('idx_invoice_history_event_category', table_name='invoice_history')
    op.drop_index('idx_invoice_history_created_at_desc', table_name='invoice_history')
    op.drop_index('idx_invoice_history_invoice_id', table_name='invoice_history')
    op.drop_index('ix_invoice_history_id', table_name='invoice_history')
    
    # Drop table
    op.drop_table('invoice_history')