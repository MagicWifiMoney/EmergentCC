import requests
import uuid
from datetime import datetime, timedelta

def create_test_credit_cards():
    """Create test credit cards with data for testing analytics"""
    API_BASE_URL = "https://b24cc02b-55f7-4d08-a4fd-c74e2c6f2cd5.preview.emergentagent.com"
    
    # Clear any existing cards
    print("Clearing existing cards...")
    response = requests.delete(f"{API_BASE_URL}/api/credit-cards")
    if response.status_code == 200:
        print("✅ Successfully cleared existing cards")
    else:
        print(f"❌ Failed to clear cards: {response.status_code} - {response.text}")
    
    # Create test cards
    test_cards = [
        {
            "id": str(uuid.uuid4()),
            "card_name": "Chase Sapphire Preferred",
            "issuer": "Chase",
            "account_number": "1234",
            "open_date": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
            "status": "Active",
            "credit_limit": 10000,
            "current_balance": 2500,
            "annual_fee": 95,
            "account_type": "Credit Card"
        },
        {
            "id": str(uuid.uuid4()),
            "card_name": "Amex Gold Card",
            "issuer": "American Express",
            "account_number": "5678",
            "open_date": (datetime.now() - timedelta(days=365*3)).strftime("%Y-%m-%d"),
            "status": "Active",
            "credit_limit": 15000,
            "current_balance": 6000,
            "annual_fee": 250,
            "account_type": "Credit Card"
        },
        {
            "id": str(uuid.uuid4()),
            "card_name": "Discover It",
            "issuer": "Discover",
            "account_number": "9012",
            "open_date": (datetime.now() - timedelta(days=365*5)).strftime("%Y-%m-%d"),
            "status": "Active",
            "credit_limit": 8000,
            "current_balance": 1000,
            "annual_fee": 0,
            "account_type": "Credit Card"
        },
        {
            "id": str(uuid.uuid4()),
            "card_name": "Capital One Venture",
            "issuer": "Capital One",
            "account_number": "3456",
            "open_date": (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
            "status": "Active",
            "credit_limit": 12000,
            "current_balance": 500,
            "annual_fee": 95,
            "account_type": "Credit Card"
        },
        {
            "id": str(uuid.uuid4()),
            "card_name": "Citi Double Cash",
            "issuer": "Citi",
            "account_number": "7890",
            "open_date": (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d"),
            "status": "Active",
            "credit_limit": 7500,
            "current_balance": 3000,
            "annual_fee": 0,
            "account_type": "Credit Card"
        }
    ]
    
    print(f"Creating {len(test_cards)} test credit cards...")
    success_count = 0
    
    for card in test_cards:
        response = requests.post(
            f"{API_BASE_URL}/api/credit-cards",
            json=card
        )
        if response.status_code == 200:
            success_count += 1
            print(f"✅ Created card: {card['card_name']}")
        else:
            print(f"❌ Failed to create card {card['card_name']}: {response.status_code} - {response.text}")
    
    print(f"✅ Created {success_count}/{len(test_cards)} test credit cards")
    return success_count == len(test_cards)

if __name__ == "__main__":
    create_test_credit_cards()
