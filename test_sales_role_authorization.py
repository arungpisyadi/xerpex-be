#!/usr/bin/env python3
"""
Comprehensive test script to validate sales role authorization changes.
Tests the changes made to allow sales role to fetch/get users on user endpoints.
"""

import requests
import json
from datetime import datetime
import time
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8001"
API_V1_STR = "/api/v1"

# Test credentials from project rules
ADMIN_CREDENTIALS = {
    "username": "admin@tugugroup.co.id",
    "password": "1q2w3e4r5t"
}

class APITester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.api_url = base_url + API_V1_STR
        self.admin_token = None
        self.sales_token = None
        self.user_token = None
        self.admin_user_id = None
        self.sales_user_id = None
        self.regular_user_id = None
        
    def login(self, username: str, password: str) -> Optional[str]:
        """Login and return JWT token"""
        url = f"{self.api_url}/auth/login/json"
        data = {"email": username, "password": password}
        
        try:
            response = requests.post(url, json=data)
            if response.status_code == 200:
                token_data = response.json()
                return token_data.get("access_token")
            else:
                print(f"❌ Login failed: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ Login request failed: {str(e)}")
            return None
    
    def get_headers(self, token: str) -> Dict[str, str]:
        """Get authorization headers with token"""
        return {"Authorization": f"Bearer {token}"}
    
    def create_user(self, token: str, username: str, email: str, full_name: str, role: str) -> Optional[Dict[str, Any]]:
        """Create a new user"""
        url = f"{self.api_url}/users"
        headers = self.get_headers(token)
        data = {
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": "testpassword123",
            "role": role
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 201:
                return response.json()
            else:
                print(f"❌ User creation failed: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"❌ User creation request failed: {str(e)}")
            return None
    
    def setup_test_users(self):
        """Setup test users for different roles"""
        print("🔧 Setting up test users...")
        
        # Login as admin
        self.admin_token = self.login(ADMIN_CREDENTIALS["username"], ADMIN_CREDENTIALS["password"])
        if not self.admin_token:
            print("❌ Failed to login as admin - cannot proceed with tests")
            return False
        
        # Get admin user details
        try:
            response = requests.get(f"{self.api_url}/auth/me", headers=self.get_headers(self.admin_token))
            if response.status_code == 200:
                admin_data = response.json()
                self.admin_user_id = admin_data.get("id")
                print(f"✅ Admin login successful (ID: {self.admin_user_id})")
            else:
                print(f"❌ Failed to get admin details: {response.status_code}")
        except:
            pass
        
        # Create sales user with unique email
        timestamp = int(time.time())
        sales_email = f"testsales{timestamp}@example.com"
        sales_user = self.create_user(
            self.admin_token,
            f"testsales{timestamp}",
            sales_email,
            "Test Sales User",
            "sales"
        )
        if sales_user:
            self.sales_user_id = sales_user["id"]
            # Login as sales user using EMAIL, not username
            self.sales_token = self.login(sales_email, "testpassword123")
            if self.sales_token:
                print(f"✅ Sales user created and authenticated (ID: {self.sales_user_id})")
            else:
                print(f"❌ Failed to authenticate sales user (ID: {self.sales_user_id})")
                return False
        else:
            print("❌ Failed to create sales user")
            return False
        
        # Create regular user with unique email
        user_email = f"testuser{timestamp}@example.com"
        regular_user = self.create_user(
            self.admin_token,
            f"testuser{timestamp}",
            user_email,
            "Test Regular User",
            "user"
        )
        if regular_user:
            self.regular_user_id = regular_user["id"]
            # Login as regular user using EMAIL, not username
            self.user_token = self.login(user_email, "testpassword123")
            if self.user_token:
                print(f"✅ Regular user created and authenticated (ID: {self.regular_user_id})")
            else:
                print(f"❌ Failed to authenticate regular user (ID: {self.regular_user_id})")
                return False
        else:
            print("❌ Failed to create regular user")
            return False
        
        return True
    
    def test_endpoint(self, method: str, endpoint: str, token: str, role_name: str, expected_status: int, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test an endpoint and return result"""
        url = f"{self.api_url}{endpoint}"
        headers = self.get_headers(token)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            status = response.status_code
            success = status == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "method": method.upper(),
                "endpoint": endpoint,
                "role": role_name,
                "expected_status": expected_status,
                "actual_status": status,
                "success": success,
                "response": response_data
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "method": method.upper(),
                "endpoint": endpoint,
                "role": role_name,
                "expected_status": expected_status,
                "actual_status": "ERROR",
                "success": False,
                "response": str(e)
            }
    
    def run_comprehensive_tests(self):
        """Run comprehensive authorization tests"""
        print("\n🧪 Starting comprehensive authorization tests...\n")
        
        results = []
        
        # Test 1: GET /users (list all users)
        print("📋 Testing GET /users endpoint...")
        results.extend([
            self.test_endpoint("GET", "/users", self.admin_token, "admin", 200),
            self.test_endpoint("GET", "/users", self.sales_token, "sales", 200),  # Should work now!
            self.test_endpoint("GET", "/users", self.user_token, "user", 403)     # Should still be forbidden
        ])
        
        # Test 2: GET /users/{user_id} (get specific user)
        print("👤 Testing GET /users/{user_id} endpoint...")
        results.extend([
            # Admin can access any user
            self.test_endpoint("GET", f"/users/{self.sales_user_id}", self.admin_token, "admin", 200),
            # Sales can access any user (new permission)
            self.test_endpoint("GET", f"/users/{self.admin_user_id}", self.sales_token, "sales", 200),
            self.test_endpoint("GET", f"/users/{self.regular_user_id}", self.sales_token, "sales", 200),
            # Regular user can only access their own profile
            self.test_endpoint("GET", f"/users/{self.regular_user_id}", self.user_token, "user", 200),
            self.test_endpoint("GET", f"/users/{self.sales_user_id}", self.user_token, "user", 403),
        ])
        
        # Test 3: POST /users (create user) - should still be admin only
        print("➕ Testing POST /users endpoint...")
        timestamp = int(time.time())
        new_user_data = {
            "username": f"tempuser{timestamp}",
            "email": f"tempuser{timestamp}@example.com",
            "full_name": "Temporary User",
            "password": "temppassword123",
            "role": "user"
        }
        results.extend([
            self.test_endpoint("POST", "/users", self.admin_token, "admin", 201, new_user_data),
            self.test_endpoint("POST", "/users", self.sales_token, "sales", 403, {**new_user_data, "username": f"tempsales{timestamp}", "email": f"tempsales{timestamp}@example.com"}),
            self.test_endpoint("POST", "/users", self.user_token, "user", 403, {**new_user_data, "username": f"tempregular{timestamp}", "email": f"tempregular{timestamp}@example.com"})
        ])
        
        # Test 4: PUT /users/{user_id} (update user) - admin or self only
        print("✏️ Testing PUT /users/{user_id} endpoint...")
        update_data = {"full_name": "Updated Name"}
        results.extend([
            # Admin can update any user
            self.test_endpoint("PUT", f"/users/{self.sales_user_id}", self.admin_token, "admin", 200, update_data),
            # Sales user cannot update other users
            self.test_endpoint("PUT", f"/users/{self.regular_user_id}", self.sales_token, "sales", 403, update_data),
            # Sales user can update themselves
            self.test_endpoint("PUT", f"/users/{self.sales_user_id}", self.sales_token, "sales", 200, update_data),
            # Regular user can update themselves
            self.test_endpoint("PUT", f"/users/{self.regular_user_id}", self.user_token, "user", 200, update_data),
            # Regular user cannot update others
            self.test_endpoint("PUT", f"/users/{self.sales_user_id}", self.user_token, "user", 403, update_data)
        ])
        
        # Test 5: DELETE /users/{user_id} - should still be admin only
        print("🗑️ Testing DELETE /users/{user_id} endpoint...")
        # First, create a user to delete with unique email
        timestamp = int(time.time())
        delete_test_user = self.create_user(
            self.admin_token,
            f"deleteuser{timestamp}",
            f"deleteuser{timestamp}@example.com",
            "Delete Test User",
            "user"
        )
        if delete_test_user:
            delete_user_id = delete_test_user["id"]
            results.extend([
                self.test_endpoint("DELETE", f"/users/{delete_user_id}", self.sales_token, "sales", 403),
                self.test_endpoint("DELETE", f"/users/{delete_user_id}", self.user_token, "user", 403),
                # Admin can delete (but not themselves)
                self.test_endpoint("DELETE", f"/users/{delete_user_id}", self.admin_token, "admin", 204)
            ])
        
        return results
    
    def print_results(self, results):
        """Print test results in a readable format"""
        print("\n" + "="*80)
        print("🧪 TEST RESULTS SUMMARY")
        print("="*80)
        
        passed = 0
        failed = 0
        
        for result in results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} | {result['method']} {result['endpoint']} | {result['role']} role")
            print(f"       Expected: {result['expected_status']}, Got: {result['actual_status']}")
            
            if not result["success"]:
                print(f"       Response: {str(result['response'])[:100]}...")
                failed += 1
            else:
                passed += 1
            print()
        
        print("="*80)
        print(f"📊 FINAL SUMMARY: {passed} PASSED, {failed} FAILED")
        print("="*80)
        
        # Specific validation for sales role changes
        print("\n🎯 SALES ROLE AUTHORIZATION VALIDATION:")
        print("-" * 50)
        
        # Check if sales can now GET users
        sales_get_users = next((r for r in results if r["method"] == "GET" and r["endpoint"] == "/users" and r["role"] == "sales"), None)
        if sales_get_users and sales_get_users["success"]:
            print("✅ Sales role can now GET /users (NEW PERMISSION)")
        else:
            print("❌ Sales role still cannot GET /users (FAILED)")
        
        # Check if sales can GET individual users
        sales_get_user = next((r for r in results if r["method"] == "GET" and "/users/" in r["endpoint"] and r["role"] == "sales"), None)
        if sales_get_user and sales_get_user["success"]:
            print("✅ Sales role can now GET /users/{id} (NEW PERMISSION)")
        else:
            print("❌ Sales role still cannot GET /users/{id} (FAILED)")
        
        # Check that sales still cannot create/update/delete
        sales_restrictions = [
            ("POST", "/users", "create users"),
            ("DELETE", "/users/", "delete users"),
        ]
        
        for method, endpoint_pattern, description in sales_restrictions:
            restricted_test = next((r for r in results if r["method"] == method and endpoint_pattern in r["endpoint"] and r["role"] == "sales"), None)
            if restricted_test and not restricted_test["success"] and restricted_test["actual_status"] == 403:
                print(f"✅ Sales role still cannot {description} (RESTRICTION MAINTAINED)")
            else:
                print(f"❌ Sales role restriction for {description} may be broken")

def main():
    """Main test function"""
    print("🚀 Starting Sales Role Authorization Test Suite")
    print(f"📡 Testing against: {BASE_URL}")
    print(f"⏰ Test started at: {datetime.now()}")
    
    tester = APITester()
    
    # Setup test users
    if not tester.setup_test_users():
        print("❌ Failed to setup test users - aborting tests")
        return
    
    # Run comprehensive tests
    results = tester.run_comprehensive_tests()
    
    # Print results
    tester.print_results(results)
    
    print(f"\n⏰ Test completed at: {datetime.now()}")

if __name__ == "__main__":
    main()