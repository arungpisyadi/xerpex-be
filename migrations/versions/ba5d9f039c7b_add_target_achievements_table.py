"""add target_achievements table

Revision ID: ba5d9f039c7b
Revises: a8eb683512bd
Create Date: 2025-09-05 18:29:54.020160

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba5d9f039c7b'
down_revision: Union[str, None] = 'a8eb683512bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create target_achievements table
    op.create_table(
        'target_achievements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('achieved_amount', sa.Numeric(precision=15, scale=2), nullable=False, default=0),
        sa.Column('target_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('achievement_percentage', sa.Numeric(precision=5, scale=2), nullable=False, default=0),
        sa.Column('calculated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_target_achievements_id'), 'target_achievements', ['id'], unique=False)


def downgrade() -> None:
    # Drop target_achievements table
    op.drop_table('target_achievements')