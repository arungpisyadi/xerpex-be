#!/usr/bin/env python
"""
Simple script to add a new admin user to the XerpeX ERP System.
Usage: python add_admin_simple.py --email admin@example.com --password securepassword [--username admin_user] [--full_name "Admin User"]

This script requires the application environment to be set up.
"""
import argparse
import sys
import uuid
from datetime import datetime

# Import from the app
try:
    from app.database import SessionLocal
    from app.models.user import User, UserActivity
    
    # Try to import from app.utils.security, but if it fails, define our own function
    try:
        from app.utils.security import get_password_hash
    except ImportError:
        from passlib.context import CryptContext
        # Configure bcrypt with specific settings to avoid version compatibility issues
        # Monkey patch for bcrypt 4.x compatibility with passlib
        import bcrypt
        if not hasattr(bcrypt, '__about__'):
            bcrypt.__about__ = type('obj', (object,), {
                '__version__': bcrypt.__version__
            })
            
        pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__ident="2b",  # Use the 2b identifier which is widely supported
            bcrypt__min_rounds=12  # Set minimum rounds for security
        )
        
        def get_password_hash(password: str) -> str:
            """Hash a password"""
            return pwd_context.hash(password)
except ImportError:
    print("Error: Could not import required modules from the application.")
    print("Make sure you're running this script from the project root directory.")
    print("If you're having issues with dependencies, try using add_admin_standalone.py instead.")
    sys.exit(1)


def create_admin_user(email, password, username=None, full_name=None):
    """Create a new admin user in the database"""
    # Create database session
    db = SessionLocal()
    
    try:
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
        now = datetime.utcnow()
        hashed_password = get_password_hash(password)
        
        # Create user object
        user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role="admin",
            is_active=True,
            created_at=now,
            updated_at=now
        )
        
        # Add user to database
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log user creation
        activity = UserActivity(
            user_id=user.id,
            activity_type="registration",
            description="Admin user created via script",
            created_at=now
        )
        db.add(activity)
        db.commit()
        
        # Capture user information before closing the session
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
        print(f"Error creating admin user: {str(e)}")
        sys.exit(1)
    
    finally:
        if db.is_active:
            db.close()


def main():
    """Parse command line arguments and create admin user"""
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
    
    # Create admin user
    user_info = create_admin_user(
        email=args.email,
        password=args.password,
        username=args.username,
        full_name=args.full_name
    )
    
    print(f"Admin user created successfully:")
    print(f"  ID: {user_info['id']}")
    print(f"  Username: {user_info['username']}")
    print(f"  Email: {user_info['email']}")
    print(f"  Role: {user_info['role']}")


if __name__ == "__main__":
    main()