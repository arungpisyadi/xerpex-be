"""add_sales_person_id_to_quotes_table

Revision ID: 012
Revises: db8036d1c9c6
Create Date: 2025-09-23 12:17:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = 'db8036d1c9c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sales_person_id column to quotes table
    op.add_column('quotes', sa.Column('sales_person_id', sa.Integer(), nullable=True))

    # Add foreign key constraint to users.id with CASCADE delete
    op.create_foreign_key(
        'fk_quotes_sales_person_id',
        'quotes',
        'users',
        ['sales_person_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add index for performance
    op.create_index(
        op.f('ix_quotes_sales_person_id'),
        'quotes',
        ['sales_person_id'],
        unique=False
    )


def downgrade() -> None:
    # Remove index
    op.drop_index(op.f('ix_quotes_sales_person_id'), table_name='quotes')

    # Drop foreign key constraint
    op.drop_constraint('fk_quotes_sales_person_id', 'quotes', type_='foreignkey')

    # Remove sales_person_id column
    op.drop_column('quotes', 'sales_person_id')