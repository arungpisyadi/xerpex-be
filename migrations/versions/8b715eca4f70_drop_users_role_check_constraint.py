"""Drop users role check constraint

Revision ID: 8b715eca4f70
Revises: 7f201e1e6af5
Create Date: 2025-09-07 21:07:44.634407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b715eca4f70'
down_revision: Union[str, None] = '7f201e1e6af5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the check constraint on users.role column
    op.drop_constraint('users_chk_1', 'users', type_='check')


def downgrade() -> None:
    # Recreate the check constraint on users.role column
    op.create_check_constraint('users_chk_1', 'users', "role IN ('admin', 'manager', 'staff')")