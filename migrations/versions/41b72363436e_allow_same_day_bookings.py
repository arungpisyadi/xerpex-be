"""allow_same_day_bookings

Revision ID: 41b72363436e
Revises: 9ef71c733bc1
Create Date: 2026-01-27 16:22:57.588350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41b72363436e'
down_revision: Union[str, None] = '9ef71c733bc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new constraint allowing same-day bookings
    # Note: Constraint may not exist yet since it was only defined in the model
    try:
        op.drop_constraint('check_booking_dates', 'bookings', type_='check')
    except:
        pass  # Constraint doesn't exist, that's fine
    
    op.create_check_constraint('check_booking_dates', 'bookings', 'check_out >= check_in')


def downgrade() -> None:
    # Revert to old constraint (not allowing same-day bookings)
    op.drop_constraint('check_booking_dates', 'bookings', type_='check')
    op.create_check_constraint('check_booking_dates', 'bookings', 'check_out > check_in')