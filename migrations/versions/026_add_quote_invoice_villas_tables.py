"""Add quote_villas and invoice_villas junction tables

Revision ID: 026
Revises: 025
Create Date: 2025-11-27

This migration creates quote_villas and invoice_villas junction tables
for many-to-many relationships.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'v7w8x9y0z1a2'
down_revision: Union[str, None] = 'l3m4n5o6p7q8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create quote_villas and invoice_villas junction tables"""
    
    # Create quote_villas table
    op.create_table(
        'quote_villas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('quote_id', sa.Integer(), nullable=False),
        sa.Column('villa_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for quote_villas
    op.create_index('ix_quote_villas_id', 'quote_villas', ['id'])
    op.create_index('ix_quote_villas_quote_id', 'quote_villas', ['quote_id'])
    op.create_index('ix_quote_villas_villa_id', 'quote_villas', ['villa_id'])
    
    # Create invoice_villas table
    op.create_table(
        'invoice_villas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('villa_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for invoice_villas
    op.create_index('ix_invoice_villas_id', 'invoice_villas', ['id'])
    op.create_index('ix_invoice_villas_invoice_id', 'invoice_villas', ['invoice_id'])
    op.create_index('ix_invoice_villas_villa_id', 'invoice_villas', ['villa_id'])


def downgrade() -> None:
    """Drop quote_villas and invoice_villas junction tables"""
    
    # Drop invoice_villas table and indexes
    op.drop_index('ix_invoice_villas_villa_id', 'invoice_villas')
    op.drop_index('ix_invoice_villas_invoice_id', 'invoice_villas')
    op.drop_index('ix_invoice_villas_id', 'invoice_villas')
    op.drop_table('invoice_villas')
    
    # Drop quote_villas table and indexes
    op.drop_index('ix_quote_villas_villa_id', 'quote_villas')
    op.drop_index('ix_quote_villas_quote_id', 'quote_villas')
    op.drop_index('ix_quote_villas_id', 'quote_villas')
    op.drop_table('quote_villas')