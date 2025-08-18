"""Add salesmen and surveys tables

Revision ID: 003
Revises: 002
Create Date: 2025-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create salesmen table
    op.create_table(
        'salesmen',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_salesmen_id'), 'salesmen', ['id'], unique=False)
    op.create_index(op.f('ix_salesmen_email'), 'salesmen', ['email'], unique=True)
    
    # Insert default salesman with id=1
    op.execute("""
        INSERT INTO salesmen (id, first_name, last_name, email, phone_number, is_active, created_at, updated_at)
        VALUES (1, 'Default', 'Salesman', 'default@xerpex.com', NULL, TRUE, NOW(), NOW())
    """)
    
    # Create surveys table
    op.create_table(
        'surveys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('estimated_paxes', sa.Integer(), nullable=False),
        sa.Column('villa_types', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='new'),
        sa.Column('priority', sa.String(length=10), nullable=True, default='medium'),
        sa.Column('follow_up_date', sa.Date(), nullable=True),
        sa.Column('visiting_date', sa.Date(), nullable=True),
        sa.Column('salesmen_id', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=sa.func.current_timestamp(), onupdate=sa.func.current_timestamp()),
        sa.ForeignKeyConstraint(['salesmen_id'], ['salesmen.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('new', 'contacted', 'scheduled', 'visited', 'quoted', 'closed_won', 'closed_lost')", name='check_survey_status'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='check_survey_priority')
    )
    op.create_index(op.f('ix_surveys_id'), 'surveys', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('surveys')
    op.drop_table('salesmen')