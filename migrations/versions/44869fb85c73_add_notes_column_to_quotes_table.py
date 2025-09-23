"""add_notes_column_to_quotes_table

Revision ID: 44869fb85c73
Revises: db8036d1c9c6
Create Date: 2025-09-17 10:56:52.435828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '44869fb85c73'
down_revision: Union[str, None] = 'db8036d1c9c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add notes column to quotes table
    op.add_column('quotes', sa.Column('notes', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove notes column from quotes table
    op.drop_column('quotes', 'notes')