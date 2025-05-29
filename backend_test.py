import requests
import unittest
import sys
import json
from datetime import datetime

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
            
            # Verify all required fields are present
            required_fields = [
                "total_cards", "active_cards", "closed_cards", 
                "average_age_years", "total_credit_limit", "total_balance", 
                "credit_utilization", "total_annual_fees", "five_24_status",
                "portfolio_analysis", "top_utilization_cards", "issuer_breakdown",
                "age_analysis"
            ]
            
            missing_fields = [field for field in required_fields if field not in response]
            if missing_fields:
                print(f"❌ Missing required fields in dashboard stats: {missing_fields}")
                self.tests_run += 1  # Count as an additional test
                return False
            
            # Verify 5/24 status fields
            if "five_24_status" in response:
                five_24_fields = [
                    "cards_in_24_months", "is_eligible", "remaining_slots",
                    "status", "recommendation"
                ]
                missing_five_24_fields = [field for field in five_24_fields if field not in response["five_24_status"]]
                if missing_five_24_fields:
                    print(f"❌ Missing required fields in 5/24 status: {missing_five_24_fields}")
                    self.tests_run += 1  # Count as an additional test
                    return False
                else:
                    print("✅ 5/24 Checker data structure verified")
                    self.tests_passed += 1  # Count as an additional test
            
            # Verify annual fees data
            if "portfolio_analysis" in response and "annual_fees" in response["portfolio_analysis"]:
                annual_fees_fields = [
                    "total", "fee_cards", "no_fee_cards", 
                    "fee_cards_count", "no_fee_cards_count"
                ]
                annual_fees = response["portfolio_analysis"]["annual_fees"]
                missing_annual_fees_fields = [field for field in annual_fees_fields if field not in annual_fees]
                if missing_annual_fees_fields:
                    print(f"❌ Missing required fields in annual fees: {missing_annual_fees_fields}")
                    self.tests_run += 1  # Count as an additional test
                    return False
                else:
                    print("✅ Annual Fees data structure verified")
                    self.tests_passed += 1  # Count as an additional test
            
            # Verify age analysis data
            if "age_analysis" in response:
                age_analysis_fields = [
                    "oldest_card_date", "newest_card_date", 
                    "average_age_months", "average_age_years"
                ]
                missing_age_fields = [field for field in age_analysis_fields if field not in response["age_analysis"]]
                if missing_age_fields:
                    print(f"❌ Missing required fields in age analysis: {missing_age_fields}")
                    self.tests_run += 1  # Count as an additional test
                    return False
                else:
                    print("✅ Credit Age Analysis data structure verified")
                    self.tests_passed += 1  # Count as an additional test
            
            # Verify issuer breakdown
            if "issuer_breakdown" in response:
                if isinstance(response["issuer_breakdown"], dict):
                    print("✅ Portfolio Diversification data structure verified")
                    self.tests_passed += 1  # Count as an additional test
                else:
                    print("❌ Issuer breakdown is not a dictionary")
                    self.tests_run += 1  # Count as an additional test
                    return False
            
            # Verify utilization alerts
            if "top_utilization_cards" in response:
                if isinstance(response["top_utilization_cards"], list):
                    if len(response["top_utilization_cards"]) > 0:
                        utilization_card_fields = ["card_name", "utilization", "balance", "limit"]
                        sample_card = response["top_utilization_cards"][0]
                        missing_util_fields = [field for field in utilization_card_fields if field not in sample_card]
                        if missing_util_fields:
                            print(f"❌ Missing required fields in utilization cards: {missing_util_fields}")
                            self.tests_run += 1  # Count as an additional test
                            return False
                    print("✅ Utilization Alerts data structure verified")
                    self.tests_passed += 1  # Count as an additional test
                else:
                    print("❌ Top utilization cards is not a list")
                    self.tests_run += 1  # Count as an additional test
                    return False
            
            return True
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
        
    def create_test_credit_cards(self):
        """Create test credit cards with data for testing analytics"""
        test_cards = [
            {
                "card_name": "Chase Sapphire Preferred",
                "issuer": "Chase",
                "account_number": "1234",
                "open_date": (datetime.now().replace(year=datetime.now().year - 1)).strftime("%Y-%m-%d"),
                "status": "Active",
                "credit_limit": 10000,
                "current_balance": 2500,
                "annual_fee": 95
            },
            {
                "card_name": "Amex Gold Card",
                "issuer": "American Express",
                "account_number": "5678",
                "open_date": (datetime.now().replace(year=datetime.now().year - 3)).strftime("%Y-%m-%d"),
                "status": "Active",
                "credit_limit": 15000,
                "current_balance": 6000,
                "annual_fee": 250
            },
            {
                "card_name": "Discover It",
                "issuer": "Discover",
                "account_number": "9012",
                "open_date": (datetime.now().replace(year=datetime.now().year - 5)).strftime("%Y-%m-%d"),
                "status": "Active",
                "credit_limit": 8000,
                "current_balance": 1000,
                "annual_fee": 0
            },
            {
                "card_name": "Capital One Venture",
                "issuer": "Capital One",
                "account_number": "3456",
                "open_date": (datetime.now().replace(month=datetime.now().month - 2)).strftime("%Y-%m-%d"),
                "status": "Active",
                "credit_limit": 12000,
                "current_balance": 500,
                "annual_fee": 95
            },
            {
                "card_name": "Citi Double Cash",
                "issuer": "Citi",
                "account_number": "7890",
                "open_date": (datetime.now().replace(year=datetime.now().year - 2)).strftime("%Y-%m-%d"),
                "status": "Active",
                "credit_limit": 7500,
                "current_balance": 3000,
                "annual_fee": 0
            }
        ]
        
        success_count = 0
        for card in test_cards:
            success, _ = self.run_test(
                f"Create Test Card: {card['card_name']}",
                "POST",
                "api/credit-cards",
                201,
                data=card
            )
            if success:
                success_count += 1
        
        print(f"✅ Created {success_count}/{len(test_cards)} test credit cards")
        return success_count == len(test_cards)

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
