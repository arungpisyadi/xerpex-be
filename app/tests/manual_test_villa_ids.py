"""
Manual integration test for villa_ids field in quotes API
This script verifies that the villa_ids field works correctly with the actual API endpoint.
"""

import sys
import os
import requests
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.config import settings

# API Configuration
BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/v1"
LOGIN_URL = f"{BASE_URL}{API_PREFIX}/auth/login/json"
QUOTES_URL = f"{BASE_URL}{API_PREFIX}/quotes"

# Test Credentials
USERNAME = "admin@tugugroup.co.id"
PASSWORD = "1q2w3e4r5t"

# Test Payload
TEST_PAYLOAD = {
    "customer_id": 9,
    "sales_person_id": 6,
    "issue_date": "2025-11-28",
    "expiry_date": "2025-12-05",
    "status": "draft",
    "total": 4400000,
    "check_in": "2025-12-12",
    "check_out": "2025-12-14",
    "villa_ids": [3, 4],
    "items": [
        {
            "package_id": 6,
            "unit_price": 400000,
            "discount": 0,
            "line_total": 2000000
        },
        {
            "package_id": 10,
            "unit_price": 800000,
            "discount": 0,
            "line_total": 2400000
        }
    ]
}


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80 + "\n")


def print_success(message):
    """Print a success message"""
    print(f"✅ {message}")


def print_error(message):
    """Print an error message"""
    print(f"❌ {message}")


def print_info(message):
    """Print an info message"""
    print(f"ℹ️  {message}")


def login():
    """Login to get authentication token"""
    print_header("Step 1: Authentication")
    print_info(f"Attempting login with username: {USERNAME}")
    
    try:
        response = requests.post(
            LOGIN_URL,
            json={"email": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/json"}
        )
        
        print_info(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print_success(f"Login successful! Token obtained: {token[:20]}...")
                return token
            else:
                print_error("Login response missing access_token")
                print(f"Response: {json.dumps(data, indent=2)}")
                return None
        else:
            print_error(f"Login failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Login request failed: {str(e)}")
        return None


def create_quote(token):
    """Create a quote with villa_ids"""
    print_header("Step 2: Create Quote with villa_ids")
    print_info("Sending POST request to /quotes/ with test payload")
    print(f"\nPayload:\n{json.dumps(TEST_PAYLOAD, indent=2)}\n")
    
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            QUOTES_URL,
            json=TEST_PAYLOAD,
            headers=headers
        )
        
        print_info(f"Response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            print_success("Quote created successfully!")
            print(f"\nResponse:\n{json.dumps(data, indent=2)}\n")
            
            quote_id = data.get("id")
            if quote_id:
                print_success(f"Quote ID: {quote_id}")
                return quote_id
            else:
                print_error("Response missing quote ID")
                return None
        else:
            print_error(f"Quote creation failed with status {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Quote creation request failed: {str(e)}")
        return None


def verify_database(quote_id):
    """Verify villa_ids were saved in the database"""
    print_header("Step 3: Database Verification")
    print_info(f"Checking quote_villas table for quote_id={quote_id}")
    
    try:
        # Create database connection
        engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Query quote_villas table
        query = text("""
            SELECT qv.quote_id, qv.villa_id, v.name as villa_name
            FROM quote_villas qv
            LEFT JOIN villas v ON qv.villa_id = v.id
            WHERE qv.quote_id = :quote_id
            ORDER BY qv.villa_id
        """)
        
        result = db.execute(query, {"quote_id": quote_id})
        rows = result.fetchall()
        
        if rows:
            print_success(f"Found {len(rows)} villa association(s) in quote_villas table:")
            print()
            for row in rows:
                villa_name = row.villa_name if row.villa_name else "Unknown"
                print(f"  - Quote ID: {row.quote_id}, Villa ID: {row.villa_id}, Villa Name: {villa_name}")
            
            # Verify the villa_ids match expectations
            saved_villa_ids = sorted([row.villa_id for row in rows])
            expected_villa_ids = sorted(TEST_PAYLOAD["villa_ids"])
            
            print()
            if saved_villa_ids == expected_villa_ids:
                print_success(f"Villa IDs match! Expected: {expected_villa_ids}, Got: {saved_villa_ids}")
                return True
            else:
                print_error(f"Villa IDs mismatch! Expected: {expected_villa_ids}, Got: {saved_villa_ids}")
                return False
        else:
            print_error(f"No villa associations found for quote_id={quote_id}")
            return False
            
    except Exception as e:
        print_error(f"Database verification failed: {str(e)}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def cleanup_quote(token, quote_id):
    """Optional: Delete the test quote"""
    print_header("Step 4: Cleanup (Optional)")
    print_info(f"Would you like to delete the test quote (ID: {quote_id})? (y/n)")
    
    # For automation, we'll skip interactive cleanup
    # Uncomment below for interactive mode
    # choice = input().strip().lower()
    # if choice == 'y':
    #     try:
    #         response = requests.delete(
    #             f"{QUOTES_URL}{quote_id}",
    #             headers={"Authorization": f"Bearer {token}"}
    #         )
    #         if response.status_code in [200, 204]:
    #             print_success("Test quote deleted successfully")
    #         else:
    #             print_error(f"Failed to delete quote: {response.status_code}")
    #     except Exception as e:
    #         print_error(f"Cleanup failed: {str(e)}")
    # else:
    #     print_info("Skipping cleanup. Quote remains in database.")
    
    print_info("Skipping automatic cleanup. Quote remains in database for manual inspection.")


def main():
    """Main test execution"""
    print_header("Manual Integration Test for villa_ids Field")
    print_info("Testing API endpoint: POST /quotes/")
    print_info(f"Base URL: {BASE_URL}")
    
    # Step 1: Login
    token = login()
    if not token:
        print_error("Cannot proceed without authentication token")
        return False
    
    # Step 2: Create quote
    quote_id = create_quote(token)
    if not quote_id:
        print_error("Cannot proceed without quote ID")
        return False
    
    # Step 3: Verify database
    verification_passed = verify_database(quote_id)
    
    # Step 4: Optional cleanup
    cleanup_quote(token, quote_id)
    
    # Final summary
    print_header("Test Summary")
    if verification_passed:
        print_success("✅ ALL TESTS PASSED!")
        print_success("The villa_ids field is working correctly with the API endpoint.")
        print_info(f"Quote ID {quote_id} was created with villa_ids [3, 4]")
        print_info("Villa associations were correctly saved in the quote_villas table")
        return True
    else:
        print_error("❌ TESTS FAILED!")
        print_error("There were issues with the villa_ids implementation")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)