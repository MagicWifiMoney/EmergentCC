
import requests
import sys
import os
import json
from datetime import datetime
import time

class CreditCardAPITester:
    def __init__(self, base_url="https://b24cc02b-55f7-4d08-a4fd-c74e2c6f2cd5.preview.emergentagent.com"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.cookies = {}

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, auth=True):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'} if not files else {}
        
        if auth and self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, cookies=self.cookies)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=headers, cookies=self.cookies)
                else:
                    response = requests.post(url, json=data, headers=headers, cookies=self.cookies)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, cookies=self.cookies)
            
            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text and response.headers.get('content-type', '').startswith('application/json') else {}
                except json.JSONDecodeError:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        return self.run_test(
            "Root API Endpoint",
            "GET",
            "/api",
            200,
            auth=False
        )

    def test_google_login_redirect(self):
        """Test Google login redirect"""
        success, _ = self.run_test(
            "Google Login Redirect",
            "GET",
            "/login/google",
            200,
            auth=False
        )
        return success

    def test_me_endpoint_unauthenticated(self):
        """Test /me endpoint without authentication"""
        success, _ = self.run_test(
            "Me Endpoint (Unauthenticated)",
            "GET",
            "/me",
            401,
            auth=False
        )
        return success

    def test_protected_endpoint_unauthenticated(self):
        """Test protected endpoint without authentication"""
        success, _ = self.run_test(
            "Protected Endpoint (Unauthenticated)",
            "GET",
            "/api/credit-cards",
            401,
            auth=False
        )
        return success

    def test_create_card_unauthenticated(self):
        """Test creating a card without authentication"""
        card_data = {
            "card_name": "Test Card",
            "issuer": "Test Bank",
            "account_number": "1234",
            "open_date": "2023-01-01",
            "status": "Active",
            "credit_limit": 5000,
            "current_balance": 1000,
            "annual_fee": 0
        }
        
        success, _ = self.run_test(
            "Create Card (Unauthenticated)",
            "POST",
            "/api/credit-cards",
            401,
            data=card_data,
            auth=False
        )
        return success

    def test_dashboard_stats_unauthenticated(self):
        """Test dashboard stats without authentication"""
        success, _ = self.run_test(
            "Dashboard Stats (Unauthenticated)",
            "GET",
            "/api/dashboard-stats",
            401,
            auth=False
        )
        return success

def main():
    # Setup
    tester = CreditCardAPITester()
    
    # Run tests for unauthenticated access
    print("\n===== Testing Unauthenticated Access =====")
    tester.test_root_endpoint()
    tester.test_google_login_redirect()
    tester.test_me_endpoint_unauthenticated()
    tester.test_protected_endpoint_unauthenticated()
    tester.test_create_card_unauthenticated()
    tester.test_dashboard_stats_unauthenticated()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    print("\n⚠️ Note: Full authentication flow tests require browser interaction")
    print("   Use the browser automation tool to test the complete OAuth flow")
    
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
