"""reorder_customers_table_columns

Revision ID: 1d08e338dae6
Revises: b6f432d4d67c
Create Date: 2025-08-22 16:12:33.616163

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d08e338dae6'
down_revision: Union[str, None] = 'b6f432d4d67c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Reorder customers table columns so phone_number and address appear after name.
    This requires recreating the table with the desired column order.
    """
    # First, drop foreign key constraints that reference customers table
    op.drop_constraint('fk_invoices_customer_id', 'invoices', type_='foreignkey')
    
    # Drop temp table if it exists (safety check)
    op.execute("DROP TABLE IF EXISTS customers_temp")
    
    # Create a temporary table with the desired column order
    op.create_table('customers_temp',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Copy data from original table to temp table with proper column order
    op.execute("""
        INSERT INTO customers_temp (id, user_id, name, email, phone_number, address, billing_address, created_at, updated_at)
        SELECT id, user_id, name, email, phone_number, address, billing_address, created_at, updated_at
        FROM customers
    """)
    
    # Drop the original table
    op.drop_table('customers')
    
    # Rename temp table to original name
    op.rename_table('customers_temp', 'customers')
    
    # Recreate indexes
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)
    
    # Recreate the foreign key constraint from invoices table
    op.create_foreign_key('fk_invoices_customer_id', 'invoices', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    """
    Revert the column reordering by recreating the table with the original column order.
    """
    # First, drop foreign key constraints that reference customers table
    op.drop_constraint('fk_invoices_customer_id', 'invoices', type_='foreignkey')
    
    # Drop temp table if it exists (safety check)
    op.execute("DROP TABLE IF EXISTS customers_temp")
    
    # Create a temporary table with the original column order
    op.create_table('customers_temp',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Copy data from current table to temp table with original column order
    op.execute("""
        INSERT INTO customers_temp (id, user_id, name, email, billing_address, created_at, updated_at, phone_number, address)
        SELECT id, user_id, name, email, billing_address, created_at, updated_at, phone_number, address
        FROM customers
    """)
    
    # Drop the current table
    op.drop_table('customers')
    
    # Rename temp table to original name
    op.rename_table('customers_temp', 'customers')
    
    # Recreate indexes
    op.create_index(op.f('ix_customers_id'), 'customers', ['id'], unique=False)
    
    # Recreate the foreign key constraint from invoices table
    op.create_foreign_key('fk_invoices_customer_id', 'invoices', 'customers', ['customer_id'], ['id'], ondelete='CASCADE')