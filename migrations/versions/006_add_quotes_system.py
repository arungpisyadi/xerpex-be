"""Add quotes and quote_items tables

Revision ID: 006
Revises: 005
Create Date: 2025-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create quotes table
    op.create_table(
        'quotes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('customer_id', sa.Integer(), nullable=False),
        sa.Column('quote_number', sa.String(length=50), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=False, default=sa.func.current_date()),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='draft'),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('tax_total', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quote_number'),
        sa.CheckConstraint("status IN ('draft', 'sent', 'accepted', 'declined', 'expired')", name='check_quote_status')
    )
    op.create_index(op.f('ix_quotes_id'), 'quotes', ['id'], unique=False)
    op.create_index(op.f('ix_quotes_quote_number'), 'quotes', ['quote_number'], unique=True)
    
    # Create quote_items table
    op.create_table(
        'quote_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), nullable=False, default=0.00),
        sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['package_id'], ['packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_quote_items_id'), 'quote_items', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('quote_items')
    op.drop_table('quotes')