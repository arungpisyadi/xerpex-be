"""
Test script for authentication flow in XerpeX ERP System
"""
import sys
import json
from typing import Dict, Any, Optional

# Try to import requests, provide helpful error if not available
try:
    import requests
except ImportError:
    print("Error: The 'requests' package is required for this script.")
    print("Please install it using: pip install requests")
    sys.exit(1)

# Base URL for API
BASE_URL = "http://localhost:8000/api/v1"

def print_separator():
    """Print a separator line"""
    print("-" * 80)

def make_request(
    method: str, 
    endpoint: str, 
    data: Optional[Dict[str, Any]] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Make an HTTP request to the API
    
    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint
        data: Request data
        token: JWT token for authentication
        
    Returns:
        Dict: Response data
    """
    url = f"{BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            print(f"Unsupported method: {method}")
            return {"error": "Unsupported method"}
        
        # Try to parse JSON response
        try:
            result = response.json()
        except json.JSONDecodeError:
            result = {"text": response.text}
        
        # Add status code to result
        result["status_code"] = response.status_code
        
        return result
    except requests.RequestException as e:
        print(f"Request error: {str(e)}")
        return {"error": str(e)}

def test_login(email: str, password: str) -> Optional[str]:
    """
    Test login functionality
    
    Args:
        email: User email
        password: User password
        
    Returns:
        str: JWT token if login successful, None otherwise
    """
    print("Testing login...")
    
    # Prepare login data
    login_data = {
        "email": email,
        "password": password
    }
    
    # Make login request
    result = make_request("POST", "/auth/login/json", login_data)
    
    # Print result
    print(f"Status code: {result.get('status_code')}")
    print(json.dumps(result, indent=2))
    
    # Return token if login successful
    if result.get("status_code") == 200 and "access_token" in result:
        return result["access_token"]
    
    return None

def test_me(token: str) -> None:
    """
    Test /me endpoint
    
    Args:
        token: JWT token
    """
    print("\nTesting /me endpoint...")
    
    # Make request to /me endpoint
    result = make_request("GET", "/auth/me", token=token)
    
    # Print result
    print(f"Status code: {result.get('status_code')}")
    print(json.dumps(result, indent=2))

def main():
    """Main function"""
    print_separator()
    print("XerpeX ERP System - Authentication Flow Test")
    print_separator()
    
    # Check if email and password are provided
    if len(sys.argv) < 3:
        print("Usage: python test_auth_flow.py <email> <password>")
        return
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    # Test login
    token = test_login(email, password)
    
    if token:
        print("\nLogin successful!")
        print(f"Token: {token}")
        
        # Test /me endpoint
        test_me(token)
    else:
        print("\nLogin failed!")
    
    print_separator()

if __name__ == "__main__":
    main()