"""merge customer fields and payments created_at

Revision ID: b6f432d4d67c
Revises: 010, 90d8352f72a4
Create Date: 2025-08-22 12:55:34.536352

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6f432d4d67c'
down_revision: Union[str, None] = ('010', '90d8352f72a4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass