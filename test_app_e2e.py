"""
Comprehensive E2E Test Suite for WAGMI Bordkasse

Tests all functionality including:
- Authentication & sessions
- Trip management  
- Crew CRUD operations
- Deposits & expenses with multi-currency
- Balance calculations & settlement
- PDF export & receipt uploads
- PWA features

Usage:
    pytest test_app_e2e.py -v
    pytest test_app_e2e.py -v -k "test_auth"  # Run specific tests
"""

import pytest
import requests
from datetime import datetime, date
import io
from test_config import BASE_URL, ADMIN_CREDENTIALS, CREW_CREDENTIALS, TEST_TIMEOUT, SUPPORTED_CURRENCIES


class SessionHelper:
    """Helper class to maintain session state across tests"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = BASE_URL
        
    def login(self, username, password):
        """Login and maintain session cookies"""
        response = self.session.post(
            f"{self.base_url}/login",
            data={"username": username, "password": password},
            timeout=TEST_TIMEOUT,
            allow_redirects=False
        )
        return response
        
    def logout(self):
        """Logout and clear session"""
        response = self.session.get(
            f"{self.base_url}/logout",
            timeout=TEST_TIMEOUT,
            allow_redirects=False
        )
        self.session.cookies.clear()
        return response
        
    def get(self, path, **kwargs):
        """GET request with session"""
        return self.session.get(f"{self.base_url}{path}", timeout=TEST_TIMEOUT, **kwargs)
        
    def post(self, path, **kwargs):
        """POST request with session"""
        return self.session.post(f"{self.base_url}{path}", timeout=TEST_TIMEOUT, **kwargs)
        
    def delete(self, path, **kwargs):
        """DELETE request with session"""
        return self.session.delete(f"{self.base_url}{path}", timeout=TEST_TIMEOUT, **kwargs)


@pytest.fixture
def admin_session():
    """Fixture providing authenticated admin session"""
    session = SessionHelper()
    response = session.login(ADMIN_CREDENTIALS["username"], ADMIN_CREDENTIALS["password"])
    assert response.status_code == 303, f"Admin login failed: {response.status_code}"
    return session


@pytest.fixture
def crew_session():
    """Fixture providing authenticated crew session"""
    session = SessionHelper()
    response = session.login(CREW_CREDENTIALS["username"], CREW_CREDENTIALS["password"])
    assert response.status_code == 303, f"Crew login failed: {response.status_code}"
    return session


@pytest.fixture
def test_crew_member(admin_session):
    """Fixture that creates a test crew member and returns its ID"""
    timestamp = datetime.now().strftime('%H%M%S%f')
    code = f"T{timestamp}"
    
    response = admin_session.post("/crew/new", data={
        "code": code,
        "name": f"Test Member {timestamp}",
        "iban_or_handle": "DE89370400440532013000"
    }, allow_redirects=True)
    
    response = admin_session.get("/crew")
    import re
    match = re.search(rf'href="/crew/(\d+).*?{code}', response.text, re.DOTALL)
    if match:
        return {"id": match.group(1), "code": code}
    return None


class TestAuthentication:
    """Test authentication and session management"""
    
    def test_login_page_accessible(self):
        """Login page should be accessible without authentication"""
        response = requests.get(f"{BASE_URL}/login", timeout=TEST_TIMEOUT)
        assert response.status_code == 200
        assert "WAGMI BORDKASSE" in response.text or "Login" in response.text
    
    def test_admin_login_success(self):
        """Admin should be able to login with correct credentials"""
        session = SessionHelper()
        response = session.login(ADMIN_CREDENTIALS["username"], ADMIN_CREDENTIALS["password"])
        assert response.status_code == 303
        assert response.headers.get("Location") == "/"
    
    def test_crew_login_success(self):
        """Crew should be able to login with correct credentials"""
        session = SessionHelper()
        response = session.login(CREW_CREDENTIALS["username"], CREW_CREDENTIALS["password"])
        assert response.status_code == 303
        assert response.headers.get("Location") == "/"
    
    def test_login_failure_invalid_credentials(self):
        """Login should fail with invalid credentials"""
        session = SessionHelper()
        response = session.login("invalid", "wrong_password")
        assert response.status_code == 200
        assert "Ungültige" in response.text or "invalid" in response.text.lower()
    
    def test_protected_route_requires_auth(self):
        """Protected routes should redirect to login when not authenticated"""
        response = requests.get(f"{BASE_URL}/", timeout=TEST_TIMEOUT, allow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers.get("Location", "")
    
    def test_logout_clears_session(self):
        """Logout should clear session and redirect to login"""
        session = SessionHelper()
        session.login(ADMIN_CREDENTIALS["username"], ADMIN_CREDENTIALS["password"])
        response = session.logout()
        assert response.status_code == 303
        
        response = session.get("/", allow_redirects=False)
        assert response.status_code == 303
        assert "/login" in response.headers.get("Location", "")
    
    def test_session_persists_across_requests(self, admin_session):
        """Session should persist across multiple requests"""
        response = admin_session.get("/")
        assert response.status_code == 200
        
        response = admin_session.get("/crew")
        assert response.status_code == 200


class TestTripManagement:
    """Test trip creation, archiving, and switching"""
    
    def test_trips_page_accessible(self, admin_session):
        """Trips page should be accessible when authenticated"""
        response = admin_session.get("/trips")
        assert response.status_code == 200
    
    def test_create_new_trip(self, admin_session):
        """Should be able to create a new trip"""
        trip_name = f"Test Trip {datetime.now().strftime('%Y%m%d%H%M%S')}"
        response = admin_session.post("/trips/new", data={
            "name": trip_name,
            "start_date": date.today().isoformat()
        }, allow_redirects=False)
        assert response.status_code == 303
        assert response.headers.get("Location") == "/trips"
    
    def test_active_trip_exists(self, admin_session):
        """There should always be an active trip"""
        response = admin_session.get("/")
        assert response.status_code == 200
        assert "active" in response.text.lower() or "trip" in response.text.lower()
    
    def test_archive_trip(self, admin_session):
        """Should be able to archive a trip"""
        trip_name = f"Archive Test {datetime.now().strftime('%Y%m%d%H%M%S')}"
        response = admin_session.post("/trips/new", data={
            "name": trip_name,
            "start_date": date.today().isoformat()
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/trips")
        import re
        match = re.search(rf'href="/trips/(\d+)/set-active".*?{trip_name}', response.text, re.DOTALL)
        assert match, "Created trip not found"
        trip_id = match.group(1)
        
        response = admin_session.post(f"/trips/{trip_id}/archive", allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/trips")
        assert "archived" in response.text.lower() or "archiv" in response.text.lower()


class TestCrewManagement:
    """Test crew member CRUD operations"""
    
    def test_crew_page_accessible(self, admin_session):
        """Crew page should be accessible"""
        response = admin_session.get("/crew")
        assert response.status_code == 200
    
    def test_create_crew_member(self, admin_session):
        """Should be able to create a new crew member"""
        timestamp = datetime.now().strftime('%H%M%S')
        response = admin_session.post("/crew/new", data={
            "code": f"TEST{timestamp}",
            "name": f"Test Crew {timestamp}",
            "iban_or_handle": "DE89370400440532013000"
        }, allow_redirects=False)
        assert response.status_code == 303
        assert response.headers.get("Location") == "/crew"
    
    def test_duplicate_crew_code_rejected(self, admin_session):
        """Duplicate crew codes should be rejected within same trip"""
        timestamp = datetime.now().strftime('%H%M%S')
        code = f"DUP{timestamp}"
        
        response1 = admin_session.post("/crew/new", data={
            "code": code,
            "name": "First Member",
            "iban_or_handle": ""
        }, allow_redirects=False)
        assert response1.status_code == 303
        
        response2 = admin_session.post("/crew/new", data={
            "code": code,
            "name": "Second Member",
            "iban_or_handle": ""
        })
        assert response2.status_code == 400 or "exists" in response2.text.lower()
    
    def test_crew_code_length_validation(self, admin_session):
        """Crew codes should support up to 20 characters"""
        response = admin_session.post("/crew/new", data={
            "code": "A" * 20,
            "name": "Long Code Test",
            "iban_or_handle": ""
        }, allow_redirects=False)
        assert response.status_code == 303


class TestDeposits:
    """Test deposit creation, editing, and multi-currency"""
    
    def test_deposits_page_accessible(self, admin_session):
        """Deposits page should be accessible"""
        response = admin_session.get("/deposits")
        assert response.status_code == 200
    
    def test_create_deposit_eur(self, admin_session, test_crew_member):
        """Should be able to create EUR deposit"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "100.00",
            "currency": "EUR",
            "deposit_date": date.today().isoformat(),
            "note": "Test EUR deposit"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/deposits")
        assert test_crew_member["code"] in response.text
        assert "100" in response.text
    
    def test_create_deposit_multi_currency(self, admin_session, test_crew_member):
        """Should be able to create deposits in different currencies"""
        for currency in ["DKK", "SEK", "GBP"]:
            response = admin_session.post("/deposits/new", data={
                "member_id": test_crew_member["id"],
                "amount": "100.00",
                "currency": currency,
                "deposit_date": date.today().isoformat(),
                "note": f"Test {currency} deposit"
            }, allow_redirects=False)
            assert response.status_code == 303
        
        response = admin_session.get("/deposits")
        assert "DKK" in response.text
        assert "SEK" in response.text
        assert "GBP" in response.text
    
    def test_deposit_eur_conversion(self, admin_session, test_crew_member):
        """Non-EUR deposits should show EUR conversion"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "100.00",
            "currency": "DKK",
            "deposit_date": date.today().isoformat(),
            "note": "DKK conversion test"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/deposits")
        assert "DKK" in response.text
        assert "€" in response.text or "EUR" in response.text


class TestExpenses:
    """Test expense creation, editing, split modes, and receipts"""
    
    def test_expenses_page_accessible(self, admin_session):
        """Expenses page should be accessible"""
        response = admin_session.get("/expenses")
        assert response.status_code == 200
    
    def test_create_expense_equal_split(self, admin_session, test_crew_member):
        """Should be able to create expense with equal split"""
        response = admin_session.post("/expenses/new", data={
            "payer_id": test_crew_member["id"],
            "category": "Lebensmittel",
            "description": "Test groceries",
            "amount": "50.00",
            "currency": "EUR",
            "expense_date": date.today().isoformat(),
            "paid_from": "wallet",
            "split_mode": "equal"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/expenses")
        assert test_crew_member["code"] in response.text
        assert "50" in response.text
    
    def test_create_expense_with_receipt(self, admin_session, test_crew_member):
        """Should be able to upload receipt with expense"""
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake pdf content")
        fake_pdf.name = "receipt.pdf"
        
        response = admin_session.post("/expenses/new", data={
            "payer_id": test_crew_member["id"],
            "category": "Sonstiges",
            "description": "Test with receipt",
            "amount": "25.00",
            "currency": "EUR",
            "expense_date": date.today().isoformat(),
            "paid_from": "private",
            "split_mode": "equal"
        }, files={
            "receipt": ("receipt.pdf", fake_pdf, "application/pdf")
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/expenses")
        assert test_crew_member["code"] in response.text
        assert "receipt" in response.text.lower() or "📎" in response.text
    
    def test_expense_multi_currency(self, admin_session, test_crew_member):
        """Should be able to create expenses in different currencies"""
        for currency in SUPPORTED_CURRENCIES:
            response = admin_session.post("/expenses/new", data={
                "payer_id": test_crew_member["id"],
                "category": "Diesel",
                "description": f"Test {currency} expense",
                "amount": "75.00",
                "currency": currency,
                "expense_date": date.today().isoformat(),
                "paid_from": "wallet",
                "split_mode": "equal"
            }, allow_redirects=False)
            assert response.status_code == 303
        
        response = admin_session.get("/expenses")
        for currency in SUPPORTED_CURRENCIES:
            assert currency in response.text


class TestBalanceAndSettlement:
    """Test balance calculations and settlement algorithm"""
    
    def test_balance_page_accessible(self, admin_session):
        """Balance page should be accessible"""
        response = admin_session.get("/balances")
        assert response.status_code == 200
    
    def test_balance_calculations_displayed(self, admin_session, test_crew_member):
        """Balance page should show calculations and calculate correctly"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "200.00",
            "currency": "EUR",
            "deposit_date": date.today().isoformat(),
            "note": "Balance test deposit"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.post("/expenses/new", data={
            "payer_id": test_crew_member["id"],
            "category": "Lebensmittel",
            "description": "Balance test expense",
            "amount": "100.00",
            "currency": "EUR",
            "expense_date": date.today().isoformat(),
            "paid_from": "wallet",
            "split_mode": "equal"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/balances")
        assert response.status_code == 200
        assert "Guthaben" in response.text or "Balance" in response.text or "Saldo" in response.text
        assert test_crew_member["code"] in response.text
        assert "200" in response.text
    
    def test_settlement_recommendations_displayed(self, admin_session, test_crew_member):
        """Settlement recommendations should be displayed when balances exist"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "150.00",
            "currency": "EUR",
            "deposit_date": date.today().isoformat(),
            "note": "Settlement test"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.get("/balances")
        assert response.status_code == 200
        assert "Ausgleich" in response.text or "Settlement" in response.text or "Transfer" in response.text


class TestExport:
    """Test PDF export functionality"""
    
    def test_export_page_accessible(self, admin_session):
        """Export page should be accessible"""
        response = admin_session.get("/export/csv")
        assert response.status_code == 200
        assert "PDF" in response.text or "Export" in response.text
    
    def test_pdf_export_downloads(self, admin_session):
        """PDF export should return valid PDF file"""
        response = admin_session.get("/export/pdf", allow_redirects=False)
        assert response.status_code == 200
        assert response.headers.get("Content-Type") == "application/pdf"
        assert len(response.content) > 0
        assert response.content.startswith(b"%PDF")
    
    def test_pdf_contains_trip_data(self, admin_session):
        """PDF should contain trip data"""
        response = admin_session.get("/export/pdf")
        assert response.status_code == 200
        content = response.content.decode('latin-1', errors='ignore')
        assert "Trip" in content or "Crew" in content or "WAGMI" in content


class TestPWA:
    """Test Progressive Web App features"""
    
    def test_manifest_accessible(self):
        """PWA manifest should be publicly accessible"""
        response = requests.get(f"{BASE_URL}/static/manifest.json", timeout=TEST_TIMEOUT)
        assert response.status_code == 200
        manifest = response.json()
        assert manifest["name"] == "WAGMI Bordkasse"
        assert manifest["short_name"] == "WAGMI"
        assert manifest["theme_color"] == "#1e3a5f"
    
    def test_pwa_icons_accessible(self):
        """PWA icons should be accessible"""
        response_192 = requests.get(f"{BASE_URL}/static/icon-192.png", timeout=TEST_TIMEOUT)
        assert response_192.status_code == 200
        assert response_192.headers.get("Content-Type") == "image/png"
        assert len(response_192.content) > 0
        
        response_512 = requests.get(f"{BASE_URL}/static/icon-512.png", timeout=TEST_TIMEOUT)
        assert response_512.status_code == 200
        assert response_512.headers.get("Content-Type") == "image/png"
        assert len(response_512.content) > 0
    
    def test_service_worker_accessible(self):
        """Service worker should be accessible"""
        response = requests.get(f"{BASE_URL}/static/sw.js", timeout=TEST_TIMEOUT)
        assert response.status_code == 200
        assert "cache" in response.text.lower() or "Cache" in response.text
    
    def test_manifest_icons_configuration(self):
        """Manifest should have correct icon configuration"""
        response = requests.get(f"{BASE_URL}/static/manifest.json", timeout=TEST_TIMEOUT)
        manifest = response.json()
        assert len(manifest["icons"]) == 2
        assert any(icon["sizes"] == "192x192" for icon in manifest["icons"])
        assert any(icon["sizes"] == "512x512" for icon in manifest["icons"])


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_delete_crew_with_deposits_blocked(self, admin_session, test_crew_member):
        """Cannot delete crew member with associated deposits"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "100.00",
            "currency": "EUR",
            "deposit_date": date.today().isoformat(),
            "note": "Test deposit to block deletion"
        }, allow_redirects=False)
        assert response.status_code == 303
        
        response = admin_session.post(f"/crew/{test_crew_member['id']}/delete", allow_redirects=False)
        assert response.status_code == 400
        assert "kann nicht gelöscht werden" in response.text or "cannot be deleted" in response.text.lower()
        assert "Einzahlungen" in response.text or "deposit" in response.text.lower()
    
    def test_invalid_currency_rejected(self, admin_session, test_crew_member):
        """Invalid currency codes should be rejected"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "100.00",
            "currency": "INVALID",
            "deposit_date": date.today().isoformat(),
            "note": "Test"
        })
        assert response.status_code == 500 or response.status_code == 422 or response.status_code == 400
        
        response = admin_session.get("/deposits")
        assert "INVALID" not in response.text
    
    def test_negative_amounts_rejected(self, admin_session, test_crew_member):
        """Negative amounts should be rejected"""
        response = admin_session.post("/deposits/new", data={
            "member_id": test_crew_member["id"],
            "amount": "-50.00",
            "currency": "EUR",
            "deposit_date": date.today().isoformat(),
            "note": "Test"
        })
        assert response.status_code == 500 or response.status_code == 422 or response.status_code == 400
        
        response = admin_session.get("/deposits")
        # Check that error message is shown or no negative deposit exists in the data
        # Use a more specific check - look for the negative amount in deposit rows, not CSS
        import re
        deposit_amounts = re.findall(r'<td[^>]*class="[^"]*text-right[^"]*"[^>]*>([-]?\d+[.,]\d+)\s*€', response.text)
        assert all(float(amt.replace(',', '.')) > 0 for amt in deposit_amounts), "Negative deposit found in list"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
