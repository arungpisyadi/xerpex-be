#!/usr/bin/env python
"""
Manual test script to verify profile update endpoints are working.
Usage: python test_profile_endpoints.py
"""
import requests
import json

BASE_URL = "http://localhost:8001/api/v1"

def test_login():
    """Test login and get access token"""
    print("=" * 50)
    print("Testing Login...")
    print("=" * 50)
    
    response = requests.post(
        f"{BASE_URL}/auth/login/json",
        json={
            "email": "admin@tugugroup.co.id",
            "password": "1q2w3e4r5t"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("Login failed!")
        return None


def test_update_personal_info(token):
    """Test updating personal information"""
    print("\n" + "=" * 50)
    print("Testing Update Personal Info...")
    print("=" * 50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.put(
        f"{BASE_URL}/auth/profile/personal-info",
        headers=headers,
        json={
            "full_name": "Test Admin User Updated",
            "phone": "081123456789"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200


def test_update_password(token):
    """Test updating password"""
    print("\n" + "=" * 50)
    print("Testing Update Password...")
    print("=" * 50)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, try to update password
    response = requests.put(
        f"{BASE_URL}/auth/profile/password",
        headers=headers,
        json={
            "current_password": "1q2w3e4r5t",
            "new_password": "newTestPassword123"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        # Test login with new password
        print("\nTesting login with new password...")
        login_response = requests.post(
            f"{BASE_URL}/auth/login/json",
            json={
                "email": "admin@tugugroup.co.id",
                "password": "newTestPassword123"
            }
        )
        
        print(f"Login Status Code: {login_response.status_code}")
        
        if login_response.status_code == 200:
            # Change password back to original
            new_token = login_response.json()["access_token"]
            print("\nChanging password back to original...")
            
            restore_response = requests.put(
                f"{BASE_URL}/auth/profile/password",
                headers={"Authorization": f"Bearer {new_token}"},
                json={
                    "current_password": "newTestPassword123",
                    "new_password": "1q2w3e4r5t"
                }
            )
            
            print(f"Restore Status Code: {restore_response.status_code}")
            return restore_response.status_code == 200
    
    return False


def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("PROFILE UPDATE ENDPOINTS TEST")
    print("=" * 50)
    
    # Test login
    token = test_login()
    if not token:
        print("\n❌ Login failed. Cannot proceed with tests.")
        return
    
    print("\n✅ Login successful!")
    
    # Test update personal info
    if test_update_personal_info(token):
        print("\n✅ Personal info update successful!")
    else:
        print("\n❌ Personal info update failed!")
    
    # Test update password
    if test_update_password(token):
        print("\n✅ Password update successful!")
    else:
        print("\n❌ Password update failed!")
    
    print("\n" + "=" * 50)
    print("ALL TESTS COMPLETED")
    print("=" * 50)


if __name__ == "__main__":
    main()