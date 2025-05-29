import requests
import unittest
import sys
import json

class CreditCardAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.text}")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test the root API endpoint"""
        success, response = self.run_test(
            "Root API Endpoint",
            "GET",
            "api",
            200
        )
        if success:
            print(f"Response: {response}")
        return success

    def test_get_credit_cards(self):
        """Test getting all credit cards"""
        success, response = self.run_test(
            "Get Credit Cards",
            "GET",
            "api/credit-cards",
            200
        )
        if success:
            print(f"Found {len(response)} credit cards")
        return success, response

    def test_get_dashboard_stats(self):
        """Test getting dashboard statistics"""
        success, response = self.run_test(
            "Get Dashboard Stats",
            "GET",
            "api/dashboard-stats",
            200
        )
        if success:
            print(f"Dashboard Stats: {json.dumps(response, indent=2)}")
        return success

    def test_clear_all_cards(self):
        """Test clearing all credit cards"""
        success, response = self.run_test(
            "Clear All Cards",
            "DELETE",
            "api/credit-cards",
            200
        )
        if success:
            print(f"Response: {response}")
        return success

def main():
    # Get the backend URL from the frontend .env file
    backend_url = "https://b24cc02b-55f7-4d08-a4fd-c74e2c6f2cd5.preview.emergentagent.com"
    
    print(f"Testing API at: {backend_url}")
    
    # Setup tester
    tester = CreditCardAPITester(backend_url)
    
    # Run tests
    print("\n=== Testing Basic API Connectivity ===")
    if not tester.test_root_endpoint():
        print("❌ Root API endpoint test failed, stopping tests")
        return 1
    
    print("\n=== Testing Credit Card Endpoints ===")
    cards_success, cards = tester.test_get_credit_cards()
    if not cards_success:
        print("❌ Get credit cards test failed")
    
    print("\n=== Testing Dashboard Stats ===")
    if not tester.test_get_dashboard_stats():
        print("❌ Get dashboard stats test failed")
    
    # Only clear cards if there are any
    if cards_success and len(cards) > 0:
        print("\n=== Testing Clear All Cards ===")
        if not tester.test_clear_all_cards():
            print("❌ Clear all cards test failed")
        
        # Verify cards were cleared
        print("\n=== Verifying Cards Cleared ===")
        verify_success, verify_cards = tester.test_get_credit_cards()
        if verify_success and len(verify_cards) == 0:
            print("✅ All cards successfully cleared")
        else:
            print("❌ Cards were not cleared properly")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
