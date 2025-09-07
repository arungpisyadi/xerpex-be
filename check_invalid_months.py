#!/usr/bin/env python3
"""
Script to check for invalid month values in the sales_targets table
"""
import os
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.models.target import Target

def check_invalid_months():
    """Check for targets with invalid month values (not 1-12)"""
    db = SessionLocal()
    try:
        # Query for invalid months
        invalid_targets = db.query(Target).filter(
            (Target.month < 1) | (Target.month > 12)
        ).all()

        if invalid_targets:
            print(f"Found {len(invalid_targets)} targets with invalid month values:")
            for target in invalid_targets:
                print(f"ID: {target.id}, User: {target.user_id}, Year: {target.year}, Month: {target.month}")
        else:
            print("No targets with invalid month values found.")

        # Also check for month = 0 or 13 specifically
        zero_months = db.query(Target).filter(Target.month == 0).count()
        thirteen_months = db.query(Target).filter(Target.month == 13).count()

        print(f"Targets with month=0: {zero_months}")
        print(f"Targets with month=13: {thirteen_months}")

    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_invalid_months()