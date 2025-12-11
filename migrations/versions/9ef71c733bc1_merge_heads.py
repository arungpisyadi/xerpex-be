"""merge heads

Revision ID: 9ef71c733bc1
Revises: c3d4e5f6g7h8, 029
Create Date: 2025-12-11 11:36:00.322172

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ef71c733bc1'
down_revision: Union[str, None] = ('c3d4e5f6g7h8', '029')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass