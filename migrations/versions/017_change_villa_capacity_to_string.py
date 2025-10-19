"""Change villa capacity field from integer to string

Revision ID: 017
Revises: 016
Create Date: 2025-10-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f9e2a1b3d4'
down_revision: Union[str, None] = '016_update_payments_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Change villa capacity from integer to string"""
    connection = op.get_bind()
    
    # For SQLite, we need to recreate the table since it doesn't support ALTER COLUMN
    # For MySQL/PostgreSQL, we can use ALTER COLUMN
    dialect = connection.dialect.name
    
    if dialect == 'sqlite':
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Create a temporary table with the new schema
        op.execute("""
            CREATE TABLE villas_new (
                id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                capacity VARCHAR(255) NOT NULL,
                room_type VARCHAR(50) NOT NULL,
                base_price NUMERIC(10, 2) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
        """)
        
        # Copy data from old table to new table
        op.execute("""
            INSERT INTO villas_new (id, name, description, capacity, room_type, base_price, is_active, created_at, updated_at)
            SELECT id, name, description, CAST(capacity AS TEXT), room_type, base_price, is_active, created_at, updated_at
            FROM villas
        """)
        
        # Drop the old table
        op.drop_table('villas')
        
        # Rename the new table
        op.rename_table('villas_new', 'villas')
    else:
        # For MySQL and PostgreSQL
        op.alter_column('villas', 'capacity',
                       existing_type=sa.Integer(),
                       type_=sa.String(255),
                       existing_nullable=False)


def downgrade() -> None:
    """Downgrade: Change villa capacity from string back to integer"""
    connection = op.get_bind()
    dialect = connection.dialect.name
    
    if dialect == 'sqlite':
        # SQLite doesn't support ALTER COLUMN, so we need to recreate the table
        # Create a temporary table with the old schema
        op.execute("""
            CREATE TABLE villas_new (
                id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                capacity INTEGER NOT NULL,
                room_type VARCHAR(50) NOT NULL,
                base_price NUMERIC(10, 2) NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id)
            )
        """)
        
        # Copy data from old table to new table, converting string to integer
        op.execute("""
            INSERT INTO villas_new (id, name, description, capacity, room_type, base_price, is_active, created_at, updated_at)
            SELECT id, name, description, CAST(capacity AS INTEGER), room_type, base_price, is_active, created_at, updated_at
            FROM villas
        """)
        
        # Drop the old table
        op.drop_table('villas')
        
        # Rename the new table
        op.rename_table('villas_new', 'villas')
    else:
        # For MySQL and PostgreSQL
        op.alter_column('villas', 'capacity',
                       existing_type=sa.String(255),
                       type_=sa.Integer(),
                       existing_nullable=False)
