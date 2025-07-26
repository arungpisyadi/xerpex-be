"""
Test script to verify database connection
"""
import sys
from sqlalchemy import create_engine, text
from app.config import settings

def test_connection():
    """Test the database connection using the configured settings"""
    print(f"Testing connection to: {settings.SQLALCHEMY_DATABASE_URI}")
    
    try:
        # Create engine
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("Connection successful!")
            print(f"Result: {result.fetchone()}")
            
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)