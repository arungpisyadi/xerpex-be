"""merge_heads

Revision ID: db8036d1c9c6
Revises: 011, a4ddf13895b3
Create Date: 2025-09-17 10:53:56.007589

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db8036d1c9c6'
down_revision: Union[str, None] = ('011', 'a4ddf13895b3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass