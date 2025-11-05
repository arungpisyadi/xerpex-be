"""Simplify booking_villas to M2M junction table

Revision ID: 021
Revises: 020
Create Date: 2025-11-04

This migration simplifies the booking_villas table to be a pure M2M junction table
with only id, booking_id, and villa_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'q2r3s4t5u6v7'
down_revision: Union[str, None] = 'p1q2r3s4t5u6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Simplify booking_villas to M2M junction table"""
    
    # Helper function to check if table exists
    def table_exists(table_name: str) -> bool:
        """Check if a table exists in the database"""
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        return table_name in inspector.get_table_names()
    
    # Drop and recreate booking_villas as simple M2M junction table
    if table_exists('booking_villas'):
        # First, save the existing villa associations
        connection = op.get_bind()
        result = connection.execute(sa.text("""
            SELECT booking_id, villa_id 
            FROM booking_villas
        """))
        villa_associations = list(result)
        
        # Drop the old table
        op.drop_table('booking_villas')
        
        # Create new simplified table
        op.create_table(
            'booking_villas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('booking_id', sa.Integer(), nullable=False),
            sa.Column('villa_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes
        op.create_index('ix_booking_villas_id', 'booking_villas', ['id'])
        op.create_index('ix_booking_villas_booking_id', 'booking_villas', ['booking_id'])
        op.create_index('ix_booking_villas_villa_id', 'booking_villas', ['villa_id'])
        
        # Restore the villa associations
        if villa_associations:
            for booking_id, villa_id in villa_associations:
                connection.execute(sa.text("""
                    INSERT INTO booking_villas (booking_id, villa_id)
                    VALUES (:booking_id, :villa_id)
                """), {'booking_id': booking_id, 'villa_id': villa_id})


def downgrade() -> None:
    """Restore booking_villas complex structure"""
    
    # Helper function to check if table exists
    def table_exists(table_name: str) -> bool:
        """Check if a table exists in the database"""
        connection = op.get_bind()
        inspector = sa.inspect(connection)
        return table_name in inspector.get_table_names()
    
    if table_exists('booking_villas'):
        # Save existing villa associations
        connection = op.get_bind()
        result = connection.execute(sa.text("""
            SELECT booking_id, villa_id 
            FROM booking_villas
        """))
        villa_associations = list(result)
        
        # Drop simplified table
        op.drop_index('ix_booking_villas_villa_id', 'booking_villas')
        op.drop_index('ix_booking_villas_booking_id', 'booking_villas')
        op.drop_index('ix_booking_villas_id', 'booking_villas')
        op.drop_table('booking_villas')
        
        # Recreate complex table
        op.create_table(
            'booking_villas',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('booking_id', sa.Integer(), nullable=False),
            sa.Column('villa_id', sa.Integer(), nullable=False),
            sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
            sa.Column('check_in', sa.Date(), nullable=True),
            sa.Column('check_out', sa.Date(), nullable=True),
            sa.Column('nightly_rate', sa.Numeric(15, 2), nullable=True),
            sa.Column('total_nights', sa.Integer(), nullable=True),
            sa.Column('villa_total', sa.Numeric(15, 2), nullable=True),
            sa.Column('assigned_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['villa_id'], ['villas.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint('check_out > check_in', name='check_booking_villa_dates'),
            sa.CheckConstraint('nightly_rate >= 0', name='check_booking_villa_rate')
        )
        
        # Restore villa associations (with NULL for new fields)
        if villa_associations:
            for booking_id, villa_id in villa_associations:
                connection.execute(sa.text("""
                    INSERT INTO booking_villas (booking_id, villa_id)
                    VALUES (:booking_id, :villa_id)
                """), {'booking_id': booking_id, 'villa_id': villa_id})