#!/usr/bin/env python
"""
Test script to verify login API endpoint
"""
import requests
import json

def test_login_api():
    """Test the login API endpoint"""
    url = "http://127.0.0.1:8001/api/v1/auth/login/json"
    
    # Test data
    payload = {
        "email": "admin@tugugroup.co.id",
        "password": "1q2w3e4r5t"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Testing login endpoint: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("-" * 60)
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("\n✓ Login successful!")
            data = response.json()
            print(f"Access Token: {data.get('access_token', 'N/A')[:50]}...")
            print(f"Token Type: {data.get('token_type', 'N/A')}")
            return True
        else:
            print(f"\n❌ Login failed with status {response.status_code}")
            try:
                error_detail = response.json()
                print(f"Error: {error_detail}")
            except:
                pass
            return False
            
    except Exception as e:
        print(f"❌ Error making request: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_login_api()
    
    if not success:
        print("\n" + "=" * 60)
        print("Debugging suggestions:")
        print("1. Check if server is running on port 8001")
        print("2. Verify the endpoint path is correct")
        print("3. Check server logs for detailed error messages")
        print("4. Verify database connection")