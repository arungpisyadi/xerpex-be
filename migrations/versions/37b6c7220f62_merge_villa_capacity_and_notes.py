"""merge_villa_capacity_and_notes

Revision ID: 37b6c7220f62
Revises: 017_change_villa_capacity_to_string, 44869fb85c73
Create Date: 2025-10-19 10:31:28.137485

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37b6c7220f62'
down_revision: Union[str, None] = ('c8f9e2a1b3d4', '44869fb85c73')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass