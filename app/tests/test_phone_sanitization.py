"""
Tests for phone number sanitization functionality
"""
import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.utils.helpers import sanitize_phone_number
from app.schemas.booking import BookingCreate, BookingUpdate, BookingVillaCreate
from app.schemas.salesmen import SalesmenCreate, SalesmenUpdate
from app.schemas.settings import GeneralSettingsCreate, GeneralSettingsUpdate
from app.schemas.survey import SurveyCreate, SurveyUpdate
from app.tests.utils import create_test_villa


class TestSanitizePhoneNumberFunction:
    """Test cases for the sanitize_phone_number function"""
    
    def test_sanitize_leading_zero_replacement(self):
        """Test replacing leading 0 with 62"""
        assert sanitize_phone_number("0812-3456-7890") == "6281234567890"
        assert sanitize_phone_number("0821 3456 7890") == "6282134567890"
        assert sanitize_phone_number("0813456789") == "62813456789"
        assert sanitize_phone_number("08123456789") == "6281234567890"
    
    def test_sanitize_plus_62_replacement(self):
        """Test replacing +62 with 62"""
        assert sanitize_phone_number("+62 812 3456 7890") == "6281234567890"
        assert sanitize_phone_number("+62-812-345-6789") == "628123456789"
        assert sanitize_phone_number("+62812345678") == "62812345678"
        assert sanitize_phone_number("+628123456789") == "628123456789"
    
    def test_sanitize_remove_hyphens_and_spaces(self):
        """Test removing hyphens and spaces"""
        assert sanitize_phone_number("812-345-6789") == "812345678"
        assert sanitize_phone_number("812 345 6789") == "812345678"
        assert sanitize_phone_number("812 - 345 - 6789") == "812345678"
        assert sanitize_phone_number("8123456789") == "8123456789"
    
    def test_sanitize_already_sanitized_numbers(self):
        """Test numbers that are already in correct format"""
        assert sanitize_phone_number("62812345678") == "62812345678"
        assert sanitize_phone_number("6281234567890") == "6281234567890"
        assert sanitize_phone_number("628123456789") == "628123456789"
    
    def test_sanitize_none_and_empty_values(self):
        """Test NULL/None and empty string values"""
        assert sanitize_phone_number(None) is None
        assert sanitize_phone_number("") is None
        assert sanitize_phone_number("   ") is None
        assert sanitize_phone_number("\t\n") is None
    
    def test_sanitize_complex_formats(self):
        """Test complex phone number formats"""
        assert sanitize_phone_number("0812-3456-7890") == "6281234567890"
        assert sanitize_phone_number("+62 812 3456 7890") == "6281234567890"
        assert sanitize_phone_number("+62-812-345-6789") == "628123456789"
        assert sanitize_phone_number("0 812 345 6789") == "6281234567890"
        assert sanitize_phone_number("+62 0812 345 678") == "620812345678"
    
    def test_sanitize_edge_cases(self):
        """Test edge cases and unusual formats"""
        # Numbers without country code or leading zero
        assert sanitize_phone_number("812345678") == "812345678"
        assert sanitize_phone_number("8123456789") == "8123456789"
        
        # Numbers with multiple spaces and hyphens
        assert sanitize_phone_number("0812  -  345  -  6789") == "6281234567890"
        assert sanitize_phone_number("+62  812  345  6789") == "6281234567890"
        
        # Very short numbers (edge case)
        assert sanitize_phone_number("0812") == "62812"
        assert sanitize_phone_number("+62812") == "62812"


class TestSchemaValidation:
    """Test phone number validation in schemas"""
    
    def test_booking_create_phone_sanitization(self, db: Session):
        """Test phone number sanitization in BookingCreate schema"""
        villa = create_test_villa(db)
        
        # Test with various phone formats
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            ("+62-812-345-6789", "628123456789"),
            ("62812345678", "62812345678"),
            (None, None),
            ("", None),
        ]
        
        for input_phone, expected_phone in test_cases:
            booking_data = BookingCreate(
                guest_name="Test Guest",
                guest_email="test@example.com",
                guest_phone=input_phone,
                check_in=date.today() + timedelta(days=1),
                check_out=date.today() + timedelta(days=3),
                total_pax=2,
                villas=[BookingVillaCreate(villa_id=villa.id)],
                packages=[],
                addons=[]
            )
            assert booking_data.guest_phone == expected_phone
    
    def test_booking_update_phone_sanitization(self):
        """Test phone number sanitization in BookingUpdate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            booking_update = BookingUpdate(guest_phone=input_phone)
            assert booking_update.guest_phone == expected_phone
    
    def test_salesmen_create_phone_sanitization(self):
        """Test phone number sanitization in SalesmenCreate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            salesmen_data = SalesmenCreate(
                first_name="John",
                last_name="Doe",
                email="john@example.com",
                phone_number=input_phone
            )
            assert salesmen_data.phone_number == expected_phone
    
    def test_salesmen_update_phone_sanitization(self):
        """Test phone number sanitization in SalesmenUpdate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            salesmen_update = SalesmenUpdate(phone_number=input_phone)
            assert salesmen_update.phone_number == expected_phone
    
    def test_general_settings_create_phone_sanitization(self):
        """Test phone number sanitization in GeneralSettingsCreate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            ("62812345678", "62812345678"),
        ]
        
        for input_phone, expected_phone in test_cases:
            settings_data = GeneralSettingsCreate(
                company_name="Test Company",
                company_address="Test Address",
                company_phone=input_phone,
                company_email="company@example.com",
                bank_account_number="1234567890",
                bank_account_holder_name="Test Company",
                bank_name="Test Bank"
            )
            assert settings_data.company_phone == expected_phone
    
    def test_general_settings_update_phone_sanitization(self):
        """Test phone number sanitization in GeneralSettingsUpdate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            settings_update = GeneralSettingsUpdate(company_phone=input_phone)
            assert settings_update.company_phone == expected_phone
    
    def test_survey_create_phone_sanitization(self):
        """Test phone number sanitization in SurveyCreate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            survey_data = SurveyCreate(
                client_name="Test Client",
                email="client@example.com",
                phone_number=input_phone,
                estimated_paxes=4
            )
            assert survey_data.phone_number == expected_phone
    
    def test_survey_update_phone_sanitization(self):
        """Test phone number sanitization in SurveyUpdate schema"""
        test_cases = [
            ("0812-3456-7890", "6281234567890"),
            ("+62 812 3456 7890", "6281234567890"),
            (None, None),
        ]
        
        for input_phone, expected_phone in test_cases:
            survey_update = SurveyUpdate(phone_number=input_phone)
            assert survey_update.phone_number == expected_phone


class TestAPIIntegration:
    """Test phone number sanitization in API endpoints"""
    
    def test_booking_create_api_phone_sanitization(self, client: TestClient, user_headers, db: Session):
        """Test phone number sanitization when creating bookings via API"""
        villa = create_test_villa(db)
        
        test_cases = [
            {
                "input": "0812-3456-7890",
                "expected": "6281234567890"
            },
            {
                "input": "+62 812 3456 7890",
                "expected": "6281234567890"
            },
            {
                "input": "+62-812-345-6789",
                "expected": "62812345678"
            }
        ]
        
        for case in test_cases:
            response = client.post(
                "/api/v1/bookings/",
                headers=user_headers,
                json={
                    "guest_name": "API Test Guest",
                    "guest_email": "apitest@example.com",
                    "guest_phone": case["input"],
                    "check_in": (date.today() + timedelta(days=1)).isoformat(),
                    "check_out": (date.today() + timedelta(days=3)).isoformat(),
                    "total_pax": 2,
                    "notes": "API phone sanitization test",
                    "villas": [{"villa_id": villa.id}],
                    "packages": [],
                    "addons": []
                }
            )
            assert response.status_code == 201
            data = response.json()
            assert data["guest_phone"] == case["expected"]
    
    def test_booking_update_api_phone_sanitization(self, client: TestClient, user_headers, db: Session):
        """Test phone number sanitization when updating bookings via API"""
        from app.tests.utils import create_test_booking
        
        booking = create_test_booking(db)
        
        response = client.put(
            f"/api/v1/bookings/{booking.id}",
            headers=user_headers,
            json={
                "guest_name": booking.guest_name,
                "guest_email": booking.guest_email,
                "guest_phone": "0812-3456-7890",
                "check_in": booking.check_in.isoformat(),
                "check_out": booking.check_out.isoformat(),
                "total_pax": booking.total_pax,
                "status": booking.status,
                "notes": booking.notes
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["guest_phone"] == "6281234567890"
    
    def test_salesmen_create_api_phone_sanitization(self, client: TestClient, admin_headers):
        """Test phone number sanitization when creating salesmen via API"""
        response = client.post(
            "/api/v1/salesmen/",
            headers=admin_headers,
            json={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "phone_number": "0812-3456-7890",
                "is_active": True
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "6281234567890"
    
    def test_salesmen_update_api_phone_sanitization(self, client: TestClient, admin_headers, db: Session):
        """Test phone number sanitization when updating salesmen via API"""
        from app.models.salesmen import Salesmen
        
        # Create a salesman
        salesman = Salesmen(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone_number="62812345678",
            is_active=True
        )
        db.add(salesman)
        db.commit()
        db.refresh(salesman)
        
        response = client.put(
            f"/api/v1/salesmen/{salesman.id}",
            headers=admin_headers,
            json={
                "first_name": "Jane",
                "last_name": "Smith",
                "email": "jane.smith@example.com",
                "phone_number": "+62 812 3456 7890",
                "is_active": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "6281234567890"
    
    def test_settings_create_api_phone_sanitization(self, client: TestClient, admin_headers):
        """Test phone number sanitization when creating settings via API"""
        response = client.post(
            "/api/v1/settings/general",
            headers=admin_headers,
            json={
                "company_name": "Test Company",
                "company_address": "Test Address",
                "company_phone": "0812-3456-7890",
                "company_email": "company@example.com",
                "bank_account_number": "1234567890",
                "bank_account_holder_name": "Test Company",
                "bank_name": "Test Bank"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["company_phone"] == "6281234567890"
    
    def test_settings_update_api_phone_sanitization(self, client: TestClient, admin_headers, db: Session):
        """Test phone number sanitization when updating settings via API"""
        from app.models.settings import GeneralSettings
        
        # Create settings
        settings = GeneralSettings(
            company_name="Old Company",
            company_address="Old Address",
            company_phone="62812345678",
            company_email="old@example.com",
            bank_account_number="0987654321",
            bank_account_holder_name="Old Company",
            bank_name="Old Bank"
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        
        response = client.put(
            f"/api/v1/settings/general/{settings.id}",
            headers=admin_headers,
            json={
                "company_name": "Updated Company",
                "company_address": "Updated Address",
                "company_phone": "+62 812 3456 7890",
                "company_email": "updated@example.com",
                "bank_account_number": "1234567890",
                "bank_account_holder_name": "Updated Company",
                "bank_name": "Updated Bank"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_phone"] == "6281234567890"
    
    def test_survey_create_api_phone_sanitization(self, client: TestClient, user_headers):
        """Test phone number sanitization when creating surveys via API"""
        response = client.post(
            "/api/v1/surveys/",
            headers=user_headers,
            json={
                "client_name": "Survey Client",
                "email": "survey@example.com",
                "phone_number": "0812-3456-7890",
                "estimated_paxes": 4,
                "villa_types": "Luxury Villa",
                "notes": "Survey test",
                "status": "new",
                "priority": "medium"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["phone_number"] == "6281234567890"
    
    def test_survey_update_api_phone_sanitization(self, client: TestClient, user_headers, db: Session):
        """Test phone number sanitization when updating surveys via API"""
        from app.models.survey import Survey
        
        # Create a survey
        survey = Survey(
            client_name="Old Client",
            email="old@example.com",
            phone_number="62812345678",
            estimated_paxes=2,
            status="new",
            priority="medium",
            salesmen_id=1
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)
        
        response = client.put(
            f"/api/v1/surveys/{survey.id}",
            headers=user_headers,
            json={
                "client_name": "Updated Client",
                "email": "updated@example.com",
                "phone_number": "+62 812 3456 7890",
                "estimated_paxes": 4,
                "status": "contacted",
                "priority": "high"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["phone_number"] == "6281234567890"


class TestPhoneNumberPersistence:
    """Test that sanitized phone numbers are properly stored and retrieved"""
    
    def test_booking_phone_persistence(self, client: TestClient, user_headers, db: Session):
        """Test that booking phone numbers are stored sanitized and retrieved correctly"""
        villa = create_test_villa(db)
        
        # Create booking with unsanitized phone
        response = client.post(
            "/api/v1/bookings/",
            headers=user_headers,
            json={
                "guest_name": "Persistence Test",
                "guest_email": "persist@example.com",
                "guest_phone": "0812-3456-7890",
                "check_in": (date.today() + timedelta(days=1)).isoformat(),
                "check_out": (date.today() + timedelta(days=3)).isoformat(),
                "total_pax": 2,
                "villas": [{"villa_id": villa.id}],
                "packages": [],
                "addons": []
            }
        )
        assert response.status_code == 201
        booking_id = response.json()["id"]
        
        # Retrieve booking and verify phone is sanitized
        response = client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["guest_phone"] == "6281234567890"
    
    def test_multiple_phone_formats_consistency(self, client: TestClient, user_headers, db: Session):
        """Test that different input formats result in consistent stored values"""
        villa = create_test_villa(db)
        
        # Test different formats that should result in the same sanitized number
        phone_formats = [
            "0812-3456-7890",
            "+62 812 3456 7890",
            "+62-812-345-6789",
            "0812 3456 7890"
        ]
        
        booking_ids = []
        for i, phone_format in enumerate(phone_formats):
            response = client.post(
                "/api/v1/bookings/",
                headers=user_headers,
                json={
                    "guest_name": f"Consistency Test {i}",
                    "guest_email": f"consistency{i}@example.com",
                    "guest_phone": phone_format,
                    "check_in": (date.today() + timedelta(days=1)).isoformat(),
                    "check_out": (date.today() + timedelta(days=3)).isoformat(),
                    "total_pax": 2,
                    "villas": [{"villa_id": villa.id}],
                    "packages": [],
                    "addons": []
                }
            )
            assert response.status_code == 201
            booking_ids.append(response.json()["id"])
        
        # Verify all bookings have the same sanitized phone number
        expected_phone = "6281234567890"  # First three should be this
        for i, booking_id in enumerate(booking_ids[:3]):
            response = client.get(f"/api/v1/bookings/{booking_id}", headers=user_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["guest_phone"] == expected_phone
        
        # The fourth one should be different (62812345678)
        response = client.get(f"/api/v1/bookings/{booking_ids[3]}", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["guest_phone"] == "62812345678"