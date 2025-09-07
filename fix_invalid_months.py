#!/usr/bin/env python3
"""
Script to fix invalid month values in the sales_targets table
"""
import os
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.target import Target

def fix_invalid_months():
    """Fix targets with invalid month values"""
    db = SessionLocal()
    try:
        # Fix month=13 -> set to 12
        month_13_targets = db.query(Target).filter(Target.month == 13).all()
        for target in month_13_targets:
            print(f"Fixing target ID {target.id}: month 13 -> 12")
            target.month = 12
            db.commit()

        # Fix month=0 -> set to 1
        month_0_targets = db.query(Target).filter(Target.month == 0).all()
        for target in month_0_targets:
            print(f"Fixing target ID {target.id}: month 0 -> 1")
            target.month = 1
            db.commit()

        print("All invalid month values have been fixed.")

    except Exception as e:
        print(f"Error fixing database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_invalid_months()