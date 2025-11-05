"""
Test booking serialization with customer relationship
"""
import requests
import json

# Base URL
BASE_URL = "http://localhost:8001/api/v1"

# Test credentials
LOGIN_URL = f"{BASE_URL}/auth/login/json"
BOOKINGS_URL = f"{BASE_URL}/bookings"

def test_booking_creation_with_customer():
    """Test that creating a booking properly serializes the customer relationship"""
    
    # Login first to get token
    login_data = {
        "username": "admin@tugugroup.co.id",
        "password": "1q2w3e4r5t"
    }
    
    print("1. Logging in...")
    login_response = requests.post(LOGIN_URL, json=login_data)
    print(f"   Status: {login_response.status_code}")
    
    if login_response.status_code != 200:
        print(f"   Error: {login_response.text}")
        return False
    
    token = login_response.json().get("access_token")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Get customers list first
    print("\n2. Getting customers...")
    customers_response = requests.get(f"{BASE_URL}/customers?active_only=true", headers=headers)
    print(f"   Status: {customers_response.status_code}")
    
    if customers_response.status_code != 200:
        print(f"   Error: {customers_response.text}")
        return False
    
    customers_data = customers_response.json()
    if not customers_data.get("customers"):
        print("   No customers found!")
        return False
    
    customer_id = customers_data["customers"][0]["id"]
    print(f"   Using customer_id: {customer_id}")
    
    # Create a booking
    print("\n3. Creating booking...")
    booking_data = {
        "customer_id": customer_id,
        "check_in": "2025-12-01",
        "check_out": "2025-12-03",
        "total_pax": 2,
        "status": "pending",
        "notes": "Test booking for serialization",
        "villas": [],
        "items": []
    }
    
    booking_response = requests.post(BOOKINGS_URL, json=booking_data, headers=headers)
    print(f"   Status: {booking_response.status_code}")
    
    if booking_response.status_code != 200 and booking_response.status_code != 201:
        print(f"   Error: {booking_response.text}")
        return False
    
    booking_result = booking_response.json()
    print(f"   Booking created successfully!")
    print(f"   Booking code: {booking_result.get('booking_code')}")
    
    # Check if customer is properly serialized
    if "customer" in booking_result:
        customer = booking_result["customer"]
        print(f"   Customer serialization: SUCCESS")
        print(f"   Customer name: {customer.get('name')}")
        print(f"   Customer type: {type(customer).__name__}")
        return True
    else:
        print(f"   Customer serialization: FAILED - customer field not found")
        return False

if __name__ == "__main__":
    success = test_booking_creation_with_customer()
    if success:
        print("\n✓ Test PASSED: Booking customer serialization works correctly")
    else:
        print("\n✗ Test FAILED: There was an issue with booking serialization")