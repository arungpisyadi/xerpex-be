#!/usr/bin/env python
"""
Script to update the password for an existing admin user.
Usage: python update_admin_password.py --email admin@tugugroup.co.id --password 1q2w3e4r5t
"""
import argparse
import sys
from datetime import datetime

# Import from the app
try:
    from app.database import SessionLocal
    from app.models.user import User
    from app.utils.security import get_password_hash
except ImportError:
    print("Error: Could not import required modules from the application.")
    print("Make sure you're running this script from the project root directory.")
    sys.exit(1)


def update_user_password(email, new_password):
    """Update password for an existing user"""
    # Create database session
    db = SessionLocal()
    
    try:
        # Find the user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: User with email '{email}' not found.")
            sys.exit(1)
        
        # Update the password
        user.password_hash = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        
        # Commit changes
        db.commit()
        
        # Capture user information
        user_info = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
        
        # Close the session
        db.close()
        
        return user_info
    
    except Exception as e:
        db.rollback()
        print(f"Error updating password: {str(e)}")
        sys.exit(1)
    
    finally:
        if db.is_active:
            db.close()


def main():
    """Parse command line arguments and update password"""
    parser = argparse.ArgumentParser(description="Update password for an existing user")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--password", required=True, help="New password")
    
    args = parser.parse_args()
    
    # Validate password
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)
    
    # Update password
    user_info = update_user_password(
        email=args.email,
        new_password=args.password
    )
    
    print(f"Password updated successfully for user:")
    print(f"  ID: {user_info['id']}")
    print(f"  Username: {user_info['username']}")
    print(f"  Email: {user_info['email']}")
    print(f"  Role: {user_info['role']}")


if __name__ == "__main__":
    main()