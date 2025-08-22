"""Add user_id to packages table for user isolation

Revision ID: 007
Revises: 006
Create Date: 2025-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if user_id column already exists
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_name = 'packages'
        AND column_name = 'user_id'
        AND table_schema = DATABASE()
    """))
    column_exists = result.scalar() > 0
    
    if not column_exists:
        # Add user_id column to packages table
        # First add as nullable
        op.add_column('packages', sa.Column('user_id', sa.Integer(), nullable=True))
        
        # Set default user_id = 1 for existing packages (assuming admin user exists)
        op.execute("UPDATE packages SET user_id = 1 WHERE user_id IS NULL")
        
        # Now make it non-nullable and add foreign key constraint
        op.alter_column('packages', 'user_id', existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key('fk_packages_user_id', 'packages', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    else:
        # Column exists, just ensure it has proper constraints
        # Set default user_id = 1 for any NULL values
        op.execute("UPDATE packages SET user_id = 1 WHERE user_id IS NULL")
        
        # Make sure it's non-nullable
        op.alter_column('packages', 'user_id', existing_type=sa.Integer(), nullable=False)
        
        # Try to create foreign key constraint (ignore if it already exists)
        try:
            op.create_foreign_key('fk_packages_user_id', 'packages', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        except:
            pass  # Foreign key might already exist


def downgrade() -> None:
    # Remove foreign key constraint and user_id column
    op.drop_constraint('fk_packages_user_id', 'packages', type_='foreignkey')
    op.drop_column('packages', 'user_id')