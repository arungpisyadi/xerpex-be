"""add sales_targets table

Revision ID: a8eb683512bd
Revises: 44f7b21741a9
Create Date: 2025-09-05 18:28:56.883694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8eb683512bd'
down_revision: Union[str, None] = '44f7b21741a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create sales_targets table
    op.create_table(
        'sales_targets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('carried_over_amount', sa.Numeric(precision=15, scale=2), nullable=False, default=0),
        sa.Column('adjusted_target_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_sales_targets_id'), 'sales_targets', ['id'], unique=False)


def downgrade() -> None:
    # Drop sales_targets table
    op.drop_table('sales_targets')