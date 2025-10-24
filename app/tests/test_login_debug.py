#!/usr/bin/env python
"""
Debug script to test login credentials
"""
import sys
from app.database import SessionLocal
from app.models.user import User
from app.utils.security import verify_password

def test_login():
    """Test login with the provided credentials"""
    email = "admin@tugugroup.co.id"
    password = "1q2w3e4r5t"
    
    db = SessionLocal()
    try:
        # Try to find user by email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' NOT FOUND in database")
            print("\nListing all users in database:")
            all_users = db.query(User).all()
            if not all_users:
                print("  No users found in database!")
            else:
                for u in all_users:
                    print(f"  - ID: {u.id}, Username: {u.username}, Email: {u.email}, Role: {u.role}, Active: {u.is_active}")
            return False
        
        print(f"✓ User found:")
        print(f"  ID: {user.id}")
        print(f"  Username: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Role: {user.role}")
        print(f"  Is Active: {user.is_active}")
        print(f"  Password Hash: {user.password_hash[:50]}...")
        
        # Verify password
        password_valid = verify_password(password, user.password_hash)
        
        if password_valid:
            print(f"\n✓ Password is CORRECT")
            return True
        else:
            print(f"\n❌ Password is INCORRECT")
            print(f"   The password '{password}' does not match the stored hash")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing login credentials...")
    print(f"Email: admin@tugugroup.co.id")
    print(f"Password: 1q2w3e4r5t")
    print("-" * 60)
    
    success = test_login()
    
    print("-" * 60)
    if success:
        print("✓ Login credentials are valid!")
        sys.exit(0)
    else:
        print("❌ Login credentials are invalid!")
        print("\nSuggested fixes:")
        print("1. Run: python update_admin_password.py --email admin@tugugroup.co.id --password 1q2w3e4r5t")
        print("2. Or create user: python add_admin.py --email admin@tugugroup.co.id --password 1q2w3e4r5t")
        sys.exit(1)