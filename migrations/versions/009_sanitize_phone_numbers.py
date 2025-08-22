"""Sanitize existing phone number data

Revision ID: 009
Revises: 008
Create Date: 2025-08-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def sanitize_phone_number_sql(phone_number: str) -> str:
    """
    SQL implementation of phone number sanitization logic
    
    Rules:
    - Replace leading 0 with 62
    - Replace +62 with 62
    - Remove "-" (hyphens)
    - Remove spaces
    """
    return f"""
    CASE 
        WHEN {phone_number} IS NULL OR TRIM({phone_number}) = '' THEN {phone_number}
        ELSE 
            CASE 
                WHEN REPLACE(REPLACE({phone_number}, ' ', ''), '-', '') LIKE '+62%' THEN 
                    CONCAT('62', SUBSTRING(REPLACE(REPLACE({phone_number}, ' ', ''), '-', ''), 4))
                WHEN REPLACE(REPLACE({phone_number}, ' ', ''), '-', '') LIKE '0%' THEN 
                    CONCAT('62', SUBSTRING(REPLACE(REPLACE({phone_number}, ' ', ''), '-', ''), 2))
                ELSE 
                    REPLACE(REPLACE({phone_number}, ' ', ''), '-', '')
            END
    END
    """


def upgrade() -> None:
    """
    Sanitize existing phone number data in all relevant tables
    """
    connection = op.get_bind()
    
    # Track number of records updated for logging
    print("Starting phone number sanitization migration...")
    
    # 1. Update bookings.guest_phone
    print("Sanitizing bookings.guest_phone...")
    result = connection.execute(sa.text(f"""
        UPDATE bookings 
        SET guest_phone = {sanitize_phone_number_sql('guest_phone')}
        WHERE guest_phone IS NOT NULL 
        AND TRIM(guest_phone) != ''
        AND guest_phone != {sanitize_phone_number_sql('guest_phone')}
    """))
    print(f"Updated {result.rowcount} records in bookings.guest_phone")
    
    # 2. Update surveys.phone_number
    print("Sanitizing surveys.phone_number...")
    result = connection.execute(sa.text(f"""
        UPDATE surveys 
        SET phone_number = {sanitize_phone_number_sql('phone_number')}
        WHERE phone_number IS NOT NULL 
        AND TRIM(phone_number) != ''
        AND phone_number != {sanitize_phone_number_sql('phone_number')}
    """))
    print(f"Updated {result.rowcount} records in surveys.phone_number")
    
    # 3. Update salesmen.phone_number
    print("Sanitizing salesmen.phone_number...")
    result = connection.execute(sa.text(f"""
        UPDATE salesmen 
        SET phone_number = {sanitize_phone_number_sql('phone_number')}
        WHERE phone_number IS NOT NULL 
        AND TRIM(phone_number) != ''
        AND phone_number != {sanitize_phone_number_sql('phone_number')}
    """))
    print(f"Updated {result.rowcount} records in salesmen.phone_number")
    
    # 4. Update general_settings.company_phone
    print("Sanitizing general_settings.company_phone...")
    result = connection.execute(sa.text(f"""
        UPDATE general_settings 
        SET company_phone = {sanitize_phone_number_sql('company_phone')}
        WHERE company_phone IS NOT NULL 
        AND TRIM(company_phone) != ''
        AND company_phone != {sanitize_phone_number_sql('company_phone')}
    """))
    print(f"Updated {result.rowcount} records in general_settings.company_phone")
    
    print("Phone number sanitization migration completed successfully!")


def downgrade() -> None:
    """
    Downgrade function - Note: This migration is not easily reversible
    as we cannot restore the original unsanitized phone number formats.
    
    This is a data transformation migration that standardizes phone numbers
    to a consistent format. The original formats are lost during the upgrade.
    
    If you need to rollback this migration, you would need to restore
    from a database backup taken before running this migration.
    """
    print("WARNING: This migration cannot be automatically reversed.")
    print("The original phone number formats have been permanently transformed.")
    print("To rollback, restore from a database backup taken before this migration.")
    
    # We could potentially implement some basic reverse transformations
    # but they would be lossy and not guarantee original format restoration
    pass