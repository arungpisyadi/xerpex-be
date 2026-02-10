"""
Test for payment update fix - verifies ResponseValidationError is resolved

This test verifies that the payment update endpoint properly returns all required fields
including: id, invoice_id, amount, payment_method, payment_type, status, created_at, 
updated_at, created_by, invoice, customer, and history.
"""
import pytest
import requests
from decimal import Decimal
from datetime import date


# Test configuration
BASE_URL = "http://localhost:8001"
API_BASE = f"{BASE_URL}/api/v1"

# Test credentials from rules
TEST_USERNAME = "admin@tugugroup.co.id"
TEST_PASSWORD = "1q2w3e4r5t"

# Payment ID to test (from the error context)
TEST_PAYMENT_ID = 111


@pytest.fixture(scope="module")
def auth_token():
    """
    Authenticate and get JWT token for API requests
    """
    login_url = f"{API_BASE}/auth/login/json"
    login_data = {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    }
    
    print(f"\n=== Attempting login at {login_url} ===")
    response = requests.post(login_url, json=login_data)
    
    # Debug response
    print(f"Login Status Code: {response.status_code}")
    print(f"Login Response: {response.text}")
    
    assert response.status_code == 200, f"Login failed with status {response.status_code}: {response.text}"
    
    response_data = response.json()
    assert "access_token" in response_data, "No access_token in login response"
    
    token = response_data["access_token"]
    print(f"Successfully authenticated. Token: {token[:20]}...")
    
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """
    Create headers with authentication token
    """
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


def test_server_is_running():
    """
    Test that the server is running and accessible
    """
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        assert response.status_code == 200, f"Server not accessible at {BASE_URL}"
        print(f"✓ Server is running at {BASE_URL}")
    except requests.exceptions.ConnectionError:
        pytest.fail(f"Cannot connect to server at {BASE_URL}. Please start the server with: uvicorn app.main:app --reload --port 8001")


def test_authentication(auth_token):
    """
    Test that authentication works correctly
    """
    assert auth_token is not None
    assert len(auth_token) > 0
    print("✓ Authentication successful")


def test_get_payment(auth_headers):
    """
    Test getting a payment to verify it exists
    """
    url = f"{API_BASE}/payments/{TEST_PAYMENT_ID}"
    print(f"\n=== Getting payment {TEST_PAYMENT_ID} ===")
    
    response = requests.get(url, headers=auth_headers)
    
    print(f"GET Status Code: {response.status_code}")
    
    if response.status_code == 404:
        pytest.skip(f"Payment ID {TEST_PAYMENT_ID} not found in database. Test requires existing payment.")
    
    assert response.status_code == 200, f"Failed to get payment: {response.text}"
    
    payment_data = response.json()
    print(f"✓ Payment {TEST_PAYMENT_ID} retrieved successfully")
    print(f"  - Amount: {payment_data.get('amount')}")
    print(f"  - Method: {payment_data.get('payment_method')}")
    print(f"  - Status: {payment_data.get('status')}")
    
    return payment_data


def test_update_payment_returns_all_required_fields(auth_headers):
    """
    Test that updating a payment returns all required fields in the response.
    
    This is the main test that verifies the fix for the ResponseValidationError.
    The payment update endpoint should return a complete PaymentResponse object
    with all nested relationships properly loaded.
    """
    url = f"{API_BASE}/payments/{TEST_PAYMENT_ID}"
    print(f"\n=== Testing payment update for ID {TEST_PAYMENT_ID} ===")
    
    # First, get the current payment to get its current details
    get_response = requests.get(url, headers=auth_headers)
    
    if get_response.status_code == 404:
        pytest.skip(f"Payment ID {TEST_PAYMENT_ID} not found in database. Test requires existing payment.")
    
    assert get_response.status_code == 200, f"Failed to get payment: {get_response.text}"
    current_payment = get_response.json()
    
    # Prepare update data - we'll just update the notes field to avoid changing critical data
    update_data = {
        "amount": str(current_payment.get("amount", "1000000")),
        "payment_method": current_payment.get("payment_method", "bank_transfer"),
        "payment_date": current_payment.get("payment_date", date.today().isoformat()),
        "reference_number": current_payment.get("reference_number", ""),
        "notes": f"Updated by test at {date.today()}",
        "payment_type": current_payment.get("payment_type", "installment"),
        "status": current_payment.get("status", "partial")
    }
    
    print("Update payload:")
    print(f"  {update_data}")
    
    # Perform the update
    response = requests.put(url, json=update_data, headers=auth_headers)
    
    print(f"PUT Status Code: {response.status_code}")
    print(f"PUT Response: {response.text[:500]}")  # Print first 500 chars
    
    # Check that the request was successful
    assert response.status_code == 200, f"Payment update failed with status {response.status_code}: {response.text}"
    
    # Parse the response
    payment_response = response.json()
    
    # Required fields according to PaymentResponse schema
    required_fields = [
        'id',
        'invoice_id',
        'amount',
        'payment_method',
        'payment_type',
        'status',
        'created_at',
        'updated_at',
        'created_by',
        'invoice',
        'customer',
        'history'
    ]
    
    print("\n=== Verifying response fields ===")
    missing_fields = []
    present_fields = []
    
    for field in required_fields:
        if field in payment_response:
            present_fields.append(field)
            print(f"✓ {field}: {type(payment_response[field]).__name__}")
            
            # Additional validation for nested objects
            if field == 'created_by':
                assert isinstance(payment_response[field], dict), "created_by should be a dict"
                assert 'id' in payment_response[field], "created_by should have 'id'"
                assert 'username' in payment_response[field], "created_by should have 'username'"
                assert 'email' in payment_response[field], "created_by should have 'email'"
                print(f"  └─ created_by.username: {payment_response[field].get('username')}")
                
            elif field == 'invoice':
                if payment_response[field] is not None:
                    assert isinstance(payment_response[field], dict), "invoice should be a dict"
                    assert 'id' in payment_response[field], "invoice should have 'id'"
                    assert 'invoice_number' in payment_response[field], "invoice should have 'invoice_number'"
                    print(f"  └─ invoice.invoice_number: {payment_response[field].get('invoice_number')}")
                else:
                    print(f"  └─ invoice is null")
                    
            elif field == 'customer':
                if payment_response[field] is not None:
                    assert isinstance(payment_response[field], dict), "customer should be a dict"
                    assert 'id' in payment_response[field], "customer should have 'id'"
                    assert 'name' in payment_response[field], "customer should have 'name'"
                    print(f"  └─ customer.name: {payment_response[field].get('name')}")
                else:
                    print(f"  └─ customer is null")
                    
            elif field == 'history':
                assert isinstance(payment_response[field], list), "history should be a list"
                print(f"  └─ history count: {len(payment_response[field])}")
                
        else:
            missing_fields.append(field)
            print(f"✗ {field}: MISSING")
    
    # Assert that all required fields are present
    assert len(missing_fields) == 0, f"Missing required fields in response: {missing_fields}"
    
    print(f"\n✓ All {len(required_fields)} required fields are present in the response")
    print(f"✓ Payment update fix is working correctly!")
    
    return payment_response


def test_payment_update_preserves_data(auth_headers):
    """
    Test that updating a payment preserves existing data correctly
    """
    url = f"{API_BASE}/payments/{TEST_PAYMENT_ID}"
    print(f"\n=== Testing data preservation ===")
    
    # Get current payment
    get_response = requests.get(url, headers=auth_headers)
    
    if get_response.status_code == 404:
        pytest.skip(f"Payment ID {TEST_PAYMENT_ID} not found in database.")
    
    assert get_response.status_code == 200
    original_payment = get_response.json()
    
    original_amount = original_payment.get('amount')
    original_invoice_id = original_payment.get('invoice_id')
    
    # Update with same data
    update_data = {
        "amount": str(original_amount),
        "payment_method": original_payment.get("payment_method"),
        "payment_date": original_payment.get("payment_date"),
        "reference_number": original_payment.get("reference_number", ""),
        "notes": original_payment.get("notes", ""),
        "payment_type": original_payment.get("payment_type"),
        "status": original_payment.get("status")
    }
    
    # Perform update
    response = requests.put(url, json=update_data, headers=auth_headers)
    assert response.status_code == 200, f"Update failed: {response.text}"
    
    updated_payment = response.json()
    
    # Verify data is preserved
    assert str(updated_payment.get('amount')) == str(original_amount), "Amount changed unexpectedly"
    assert updated_payment.get('invoice_id') == original_invoice_id, "Invoice ID changed unexpectedly"
    
    print("✓ Payment data preserved correctly after update")


def test_payment_response_schema_structure():
    """
    Test that PaymentUpdate schema accepts all necessary fields
    """
    from app.schemas.payment import PaymentUpdate, PaymentMethod, PaymentType, PaymentStatus
    
    # Verify the schema can accept all fields
    update_data = PaymentUpdate(
        amount=Decimal("25000000"),
        payment_method=PaymentMethod.bank_transfer,
        payment_type=PaymentType.installment,
        status=PaymentStatus.partial,
        payment_date=date(2026, 1, 11),
        reference_number="TEST-REF-123",
        notes="Test notes"
    )
    
    # Verify the fields are set correctly
    assert update_data.amount == Decimal("25000000")
    assert update_data.payment_method == PaymentMethod.bank_transfer
    assert update_data.payment_type == PaymentType.installment
    assert update_data.status == PaymentStatus.partial
    
    print("✓ PaymentUpdate schema structure is correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
