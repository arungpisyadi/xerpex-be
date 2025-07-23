"""Add general settings table

Revision ID: 002
Revises: 001
Create Date: 2025-07-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create general_settings table
    op.create_table(
        'general_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=100), nullable=False),
        sa.Column('company_address', sa.Text(), nullable=False),
        sa.Column('company_phone', sa.String(length=20), nullable=False),
        sa.Column('company_email', sa.String(length=100), nullable=False),
        
        # Bank account details
        sa.Column('bank_account_number', sa.String(length=50), nullable=False),
        sa.Column('bank_account_holder_name', sa.String(length=100), nullable=False),
        sa.Column('bank_name', sa.String(length=100), nullable=False),
        sa.Column('bank_swift_number', sa.String(length=50), nullable=True),
        
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_general_settings_id'), 'general_settings', ['id'], unique=False)


def downgrade() -> None:
    # Drop general_settings table
    op.drop_table('general_settings')