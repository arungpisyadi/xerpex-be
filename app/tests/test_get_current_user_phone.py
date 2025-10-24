"""
Test script for verifying phone field in get_current_user endpoint
"""
import requests
import sys
import socket


def check_port_in_use(port: int) -> bool:
    """Check if a port is already in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        try:
            result = s.connect_ex(("localhost", port))
            return result == 0
        except socket.error:
            return False


def test_get_current_user_phone():
    """Test that the /auth/me endpoint returns the phone field"""
    
    # Check if server is running on port 8001
    if not check_port_in_use(8001):
        print("[FAIL] Server is not running on port 8001")
        print("Please start the server with: uvicorn app.main:app --reload --port 8001")
        return False
    
    base_url = "http://localhost:8001/api/v1"
    
    # Test credentials
    credentials = {
        "email": "admin@tugugroup.co.id",
        "password": "1q2w3e4r5t"
    }
    
    print("[INFO] Testing login with provided credentials...")
    
    # Step 1: Login to get access token
    try:
        login_response = requests.post(
            f"{base_url}/auth/login/json",
            json=credentials,
            timeout=10
        )
        
        if login_response.status_code != 200:
            print(f"[FAIL] Login failed with status code: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return False
        
        login_data = login_response.json()
        access_token = login_data.get("access_token")
        
        if not access_token:
            print("[FAIL] No access token received from login")
            return False
        
        print("[PASS] Login successful")
        
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] Login request failed: {e}")
        return False
    
    # Step 2: Get current user info
    print("\n[INFO] Testing /auth/me endpoint...")
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        me_response = requests.get(
            f"{base_url}/auth/me",
            headers=headers,
            timeout=10
        )
        
        if me_response.status_code != 200:
            print(f"[FAIL] /auth/me failed with status code: {me_response.status_code}")
            print(f"Response: {me_response.text}")
            return False
        
        user_data = me_response.json()
        
        print("[PASS] /auth/me endpoint successful")
        print("\n[INFO] User data received:")
        print(f"  - ID: {user_data.get('id')}")
        print(f"  - Username: {user_data.get('username')}")
        print(f"  - Email: {user_data.get('email')}")
        print(f"  - Full Name: {user_data.get('full_name')}")
        print(f"  - Role: {user_data.get('role')}")
        print(f"  - Is Active: {user_data.get('is_active')}")
        print(f"  - Phone: {user_data.get('phone')}")
        
        # Step 3: Verify phone field exists in response
        if "phone" in user_data:
            print("\n[PASS] SUCCESS: Phone field is present in the response")
            phone_value = user_data.get('phone')
            if phone_value:
                print(f"   Phone value: {phone_value}")
            else:
                print("   Phone value is null/empty (this is okay)")
            return True
        else:
            print("\n[FAIL] Phone field is missing from the response")
            return False
        
    except requests.exceptions.RequestException as e:
        print(f"[FAIL] /auth/me request failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Testing phone field in get_current_user endpoint")
    print("=" * 60)
    print()
    
    success = test_get_current_user_phone()
    
    print()
    print("=" * 60)
    if success:
        print("[PASS] All tests passed!")
        sys.exit(0)
    else:
        print("[FAIL] Tests failed!")
        sys.exit(1)