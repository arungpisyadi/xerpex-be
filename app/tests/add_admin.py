#!/usr/bin/env python
"""
Script to add a new admin user to the XerpeX ERP System.
Usage: python add_admin.py --email admin@example.com --password securepassword [--username admin_user] [--full_name "Admin User"]
"""
import argparse
import sys
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

# Import from the app
from app.database import SessionLocal
from app.models.user import User, UserActivity
from app.utils.security import get_password_hash


def create_admin_user(
    db: Session,
    email: str,
    password: str,
    username: str = None,
    full_name: str = None
) -> User:
    """
    Create a new admin user
    
    Args:
        db: Database session
        email: User email
        password: User password
        username: Username (optional, will be generated if not provided)
        full_name: Full name (optional)
        
    Returns:
        User: Created user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        print(f"Error: User with email '{email}' already exists.")
        sys.exit(1)
    
    # Generate username if not provided
    if not username:
        # Use part of the email as username
        username = email.split('@')[0]
        
        # Check if username exists
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            # Append a random string to make it unique
            username = f"{username}_{uuid.uuid4().hex[:6]}"
    else:
        # Check if username exists
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            print(f"Error: Username '{username}' already exists.")
            sys.exit(1)
    
    # Create new admin user
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        full_name=full_name,
        role="admin",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log user creation
    activity = UserActivity(
        user_id=db_user.id,
        activity_type="registration",
        description="Admin user created via script",
        created_at=datetime.utcnow()
    )
    db.add(activity)
    db.commit()
    
    return db_user


def main():
    """Main function to parse arguments and create admin user"""
    parser = argparse.ArgumentParser(description="Add a new admin user to the XerpeX ERP System")
    parser.add_argument("--email", required=True, help="Admin user email")
    parser.add_argument("--password", required=True, help="Admin user password")
    parser.add_argument("--username", help="Admin username (optional)")
    parser.add_argument("--full_name", help="Admin full name (optional)")
    
    args = parser.parse_args()
    
    # Validate email (basic check)
    if '@' not in args.email or '.' not in args.email:
        print("Error: Invalid email format.")
        sys.exit(1)
    
    # Validate password
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)
    
    # Create database session
    db = SessionLocal()
    try:
        # Create admin user
        user = create_admin_user(
            db=db,
            email=args.email,
            password=args.password,
            username=args.username,
            full_name=args.full_name
        )
        print(f"Admin user created successfully:")
        print(f"  ID: {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()