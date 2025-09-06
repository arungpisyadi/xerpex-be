"""add sales_person_id to invoices table

Revision ID: 7f201e1e6af5
Revises: ba5d9f039c7b
Create Date: 2025-09-05 18:30:59.856427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f201e1e6af5'
down_revision: Union[str, None] = 'ba5d9f039c7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add sales_person_id column to invoices table
    op.add_column('invoices', sa.Column('sales_person_id', sa.Integer(), nullable=True))

    # Add foreign key constraint to users table
    op.create_foreign_key('fk_invoices_sales_person_id', 'invoices', 'users', ['sales_person_id'], ['id'])


def downgrade() -> None:
    # Drop foreign key constraint
    op.drop_constraint('fk_invoices_sales_person_id', 'invoices', type_='foreignkey')

    # Drop sales_person_id column from invoices table
    op.drop_column('invoices', 'sales_person_id')