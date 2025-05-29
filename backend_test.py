
import requests
import sys
import os
import time
from datetime import datetime

class CreditCardAppTester:
    def __init__(self, base_url=None):
        # Get the backend URL from environment or use the one from frontend .env
        if base_url:
            self.base_url = base_url
        else:
            # Read from frontend .env file
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if 'REACT_APP_BACKEND_URL' in line:
                        self.base_url = line.split('=')[1].strip().strip('"')
                        break
        
        print(f"Using backend URL: {self.base_url}")
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, allow_redirects=True):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        if not headers:
            headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, allow_redirects=allow_redirects)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers, allow_redirects=allow_redirects)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers, allow_redirects=allow_redirects)
            
            # For redirects, we consider 3xx as success
            success = False
            if expected_status == 'redirect':
                success = 300 <= response.status_code < 400
                print(f"✅ Redirect status: {response.status_code}, Location: {response.headers.get('Location', 'No location header')}")
            else:
                success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.headers.get('Content-Type', '').startswith('application/json'):
                    try:
                        return success, response.json()
                    except:
                        return success, {}
                return success, response
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False, response

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, None

    def test_api_root(self):
        """Test the API root endpoint"""
        return self.run_test("API Root", "GET", "api", 200)  # Returns JSON message

    def test_google_login_redirect(self):
        """Test the Google login redirect endpoint"""
        success, response = self.run_test(
            "Google Login Redirect", 
            "GET", 
            "api/login/google", 
            'redirect',
            allow_redirects=False
        )
        
        if success:
            redirect_url = response.headers.get('Location', '')
            print(f"Redirect URL: {redirect_url}")
            
            # Verify the redirect URL contains Google OAuth
            if 'accounts.google.com' in redirect_url:
                print("✅ Redirect URL contains Google OAuth domain")
            else:
                print("❌ Redirect URL does not contain Google OAuth domain")
                success = False
        
        return success, response

    def test_auth_google_callback_endpoint(self):
        """Test the Google auth callback endpoint (without actual OAuth flow)"""
        # We can't fully test this without a real OAuth flow, but we can check if the endpoint exists
        return self.run_test(
            "Google Auth Callback Endpoint", 
            "GET", 
            "api/auth/google", 
            302,  # Should redirect to login page without valid OAuth token
            allow_redirects=False
        )

    def test_me_endpoint_unauthorized(self):
        """Test the /me endpoint without authentication"""
        return self.run_test("Me Endpoint (Unauthorized)", "GET", "api/me", 401)

    def test_protected_endpoints_unauthorized(self):
        """Test protected endpoints without authentication"""
        endpoints = [
            ("Credit Cards", "GET", "api/credit-cards"),
            ("Dashboard Stats", "GET", "api/dashboard-stats"),
            ("Upload Credit Report", "POST", "api/upload-credit-report")
        ]
        
        results = []
        for name, method, endpoint in endpoints:
            result = self.run_test(f"{name} (Unauthorized)", method, endpoint, 401)
            results.append(result)
        
        return all(r[0] for r in results)

    def test_logout_endpoint(self):
        """Test the logout endpoint"""
        return self.run_test("Logout Endpoint", "POST", "api/logout", 200)

    def test_refresh_token_endpoint_unauthorized(self):
        """Test the refresh token endpoint without a valid refresh token"""
        return self.run_test("Refresh Token (Unauthorized)", "POST", "api/refresh", 401)

    def print_summary(self):
        """Print a summary of the test results"""
        print("\n" + "="*50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        if self.tests_passed == self.tests_run:
            print("✅ All tests passed!")
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
        
        return self.tests_passed == self.tests_run

def main():
    # Setup
    tester = CreditCardAppTester()
    
    # Run tests
    tester.test_api_root()
    
    # Test authentication endpoints
    tester.test_google_login_redirect()
    tester.test_auth_google_callback_endpoint()
    tester.test_logout_endpoint()
    tester.test_refresh_token_endpoint_unauthorized()
    
    # Test protected endpoints without authentication
    tester.test_me_endpoint_unauthorized()
    tester.test_protected_endpoints_unauthorized()
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
