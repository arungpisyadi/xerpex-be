#!/usr/bin/env python
"""
Standalone script to add a new admin user to the XerpeX ERP System.
Usage: python add_admin_standalone.py --email admin@example.com --password securepassword [--username admin_user] [--full_name "Admin User"]

This script connects directly to the database without requiring the full application environment.
"""
import argparse
import os
import sys
import uuid
from datetime import datetime
import hashlib
import secrets
import base64

try:
    # Try to import required libraries
    import mysql.connector
    from dotenv import load_dotenv
    from passlib.context import CryptContext
except ImportError:
    print("Required libraries not found. Please install them using:")
    print("pip install mysql-connector-python python-dotenv passlib[bcrypt]")
    sys.exit(1)

# Load environment variables from .env file
load_dotenv()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def create_admin_user(
    conn,
    email: str,
    password: str,
    username: str = None,
    full_name: str = None
) -> dict:
    """
    Create a new admin user
    
    Args:
        conn: Database connection
        email: User email
        password: User password
        username: Username (optional, will be generated if not provided)
        full_name: Full name (optional)
        
    Returns:
        dict: Created user info
    """
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            sys.exit(1)
        
        # Generate username if not provided
        if not username:
            # Use part of the email as username
            username = email.split('@')[0]
            
            # Check if username exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_username = cursor.fetchone()
            if existing_username:
                # Append a random string to make it unique
                username = f"{username}_{uuid.uuid4().hex[:6]}"
        else:
            # Check if username exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            existing_username = cursor.fetchone()
            if existing_username:
                print(f"Error: Username '{username}' already exists.")
                sys.exit(1)
        
        # Create new admin user
        now = datetime.utcnow()
        hashed_password = get_password_hash(password)
        
        # Insert user
        cursor.execute(
            """
            INSERT INTO users 
            (username, email, password_hash, full_name, role, is_active, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                username,
                email,
                hashed_password,
                full_name or "",
                "admin",
                True,
                now,
                now
            )
        )
        
        # Get the inserted user ID
        user_id = cursor.lastrowid
        
        # Log user creation
        cursor.execute(
            """
            INSERT INTO user_activities
            (user_id, activity_type, description, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (
                user_id,
                "registration",
                "Admin user created via standalone script",
                now
            )
        )
        
        # Commit the transaction
        conn.commit()
        
        # Return user info
        return {
            "id": user_id,
            "username": username,
            "email": email,
            "role": "admin"
        }
        
    except Exception as e:
        # Rollback in case of error
        conn.rollback()
        raise e
    finally:
        cursor.close()


def get_db_connection():
    """
    Get database connection from environment variables
    
    Returns:
        Connection: MySQL database connection
    """
    try:
        # Get database connection parameters from environment variables
        db_host = os.getenv("MYSQL_SERVER")
        db_user = os.getenv("MYSQL_USER")
        db_password = os.getenv("MYSQL_PASSWORD")
        db_name = os.getenv("MYSQL_DB")
        db_port = os.getenv("MYSQL_PORT", "3306")
        
        # Check if all required parameters are available
        if not all([db_host, db_user, db_password, db_name]):
            print("Error: Database connection parameters not found in environment variables.")
            print("Make sure MYSQL_SERVER, MYSQL_USER, MYSQL_PASSWORD, and MYSQL_DB are set in .env file.")
            sys.exit(1)
        
        # Connect to the database
        conn = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=int(db_port)
        )
        
        return conn
    
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL database: {err}")
        sys.exit(1)


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
    
    # Get database connection
    conn = get_db_connection()
    
    try:
        # Create admin user
        user = create_admin_user(
            conn=conn,
            email=args.email,
            password=args.password,
            username=args.username,
            full_name=args.full_name
        )
        print(f"Admin user created successfully:")
        print(f"  ID: {user['id']}")
        print(f"  Username: {user['username']}")
        print(f"  Email: {user['email']}")
        print(f"  Role: {user['role']}")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()