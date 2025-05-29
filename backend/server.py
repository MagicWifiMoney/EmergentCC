from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import tempfile
import shutil
import pdfplumber
from openai import OpenAI
import json
import re
from collections import defaultdict


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client
openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class CreditCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    card_name: str
    issuer: str
    account_number: str  # Last 4 digits or masked
    open_date: str
    status: str  # "Active" or "Closed"
    credit_limit: Optional[float] = None
    current_balance: Optional[float] = None
    annual_fee: Optional[float] = None
    account_type: str = "Credit Card"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CreditReportUpload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    cards_extracted: int
    processing_status: str

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


def extract_pdf_text(file_path: str) -> str:
    """Extract text from PDF using pdfplumber"""
    try:
        with pdfplumber.open(file_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error extracting PDF text: {str(e)}")


async def parse_credit_cards_with_gpt4o(text: str) -> List[dict]:
    """Use OpenAI GPT-4o to extract credit card information from text"""
    try:
        system_prompt = """You are a financial data extraction expert. Extract ALL credit card accounts from the provided credit report text.

For each credit card account, extract:
- card_name: The name/product name of the credit card (e.g., "Chase Freedom", "Capital One Venture", "Discover it")
- issuer: The bank/company name (e.g., "Chase", "Capital One", "Discover", "American Express", "Citi", "Bank of America")
- account_number: Last 4 digits if available, otherwise use "****" 
- open_date: Date account was opened (format as YYYY-MM-DD if possible, or MM/YYYY)
- status: "Active" or "Closed" based on account status
- credit_limit: Credit limit amount as a number (without $, commas)
- current_balance: Current balance as a number (without $, commas)
- annual_fee: Annual fee amount as a number (without $, commas) - if not explicitly stated, use common knowledge for the card

Return ONLY a JSON array of objects. Do not include any other text.
If no credit cards are found, return an empty array [].

Example format:
[
  {
    "card_name": "Chase Freedom Unlimited",
    "issuer": "Chase",
    "account_number": "1234",
    "open_date": "2020-03-15",
    "status": "Active",
    "credit_limit": 5000,
    "current_balance": 1250,
    "annual_fee": 0
  }
]"""

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up the response to ensure valid JSON
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        
        try:
            cards_data = json.loads(result_text)
            return cards_data if isinstance(cards_data, list) else []
        except json.JSONDecodeError:
            # If JSON parsing fails, return empty list
            return []
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing with OpenAI: {str(e)}")


def calculate_5_24_status(cards: List[dict]) -> dict:
    """Calculate 5/24 eligibility for Chase cards"""
    try:
        # Count cards opened in last 24 months
        cutoff_date = datetime.now() - timedelta(days=24*30)  # Approximate 24 months
        recent_cards = []
        
        for card in cards:
            if card.get('status', '').lower() == 'active':
                open_date_str = card.get('open_date', '')
                if open_date_str and open_date_str != 'Unknown':
                    try:
                        # Try different date formats
                        for fmt in ['%Y-%m-%d', '%m/%Y', '%Y-%m', '%m-%d-%Y']:
                            try:
                                if fmt == '%m/%Y':
                                    open_date = datetime.strptime(open_date_str, fmt)
                                    # Assume first day of month for MM/YYYY format
                                    open_date = open_date.replace(day=1)
                                else:
                                    open_date = datetime.strptime(open_date_str, fmt)
                                
                                if open_date >= cutoff_date:
                                    recent_cards.append({
                                        'card_name': card.get('card_name', 'Unknown'),
                                        'issuer': card.get('issuer', 'Unknown'),
                                        'open_date': open_date_str
                                    })
                                break
                            except ValueError:
                                continue
                    except:
                        continue
        
        cards_in_24_months = len(recent_cards)
        is_eligible = cards_in_24_months < 5
        remaining_slots = max(0, 5 - cards_in_24_months)
        
        return {
            "cards_in_24_months": cards_in_24_months,
            "is_eligible": is_eligible,
            "remaining_slots": remaining_slots,
            "recent_cards": recent_cards,
            "status": "Eligible" if is_eligible else "Not Eligible",
            "recommendation": f"You can apply for {remaining_slots} more Chase cards" if is_eligible else "Wait for older cards to age out of 24-month window"
        }
    except Exception as e:
        return {
            "cards_in_24_months": 0,
            "is_eligible": True,
            "remaining_slots": 5,
            "recent_cards": [],
            "status": "Unknown",
            "recommendation": "Unable to calculate 5/24 status"
        }


def analyze_credit_portfolio(cards: List[dict]) -> dict:
    """Analyze credit card portfolio for insights"""
    if not cards:
        return {}
    
    # Cards by issuer
    issuer_breakdown = defaultdict(int)
    issuer_limits = defaultdict(float)
    
    # Active vs closed analysis
    active_cards = [c for c in cards if c.get('status', '').lower() == 'active']
    closed_cards = [c for c in cards if c.get('status', '').lower() == 'closed']
    
    # Annual fees analysis
    total_annual_fees = 0
    fee_cards = []
    no_fee_cards = []
    
    # Credit utilization by card
    utilization_breakdown = []
    
    # Age analysis
    oldest_card_date = None
    newest_card_date = None
    
    for card in cards:
        issuer = card.get('issuer', 'Unknown')
        issuer_breakdown[issuer] += 1
        
        if card.get('credit_limit'):
            issuer_limits[issuer] += card.get('credit_limit', 0)
        
        # Annual fee analysis
        annual_fee = card.get('annual_fee', 0) or 0
        total_annual_fees += annual_fee
        
        if annual_fee > 0:
            fee_cards.append({
                'card_name': card.get('card_name', 'Unknown'),
                'annual_fee': annual_fee
            })
        else:
            no_fee_cards.append(card.get('card_name', 'Unknown'))
        
        # Utilization breakdown
        if card.get('credit_limit') and card.get('current_balance') is not None:
            utilization = (card.get('current_balance', 0) / card.get('credit_limit', 1)) * 100
            utilization_breakdown.append({
                'card_name': card.get('card_name', 'Unknown'),
                'utilization': round(utilization, 1),
                'balance': card.get('current_balance', 0),
                'limit': card.get('credit_limit', 0)
            })
        
        # Age analysis
        open_date_str = card.get('open_date', '')
        if open_date_str and open_date_str != 'Unknown':
            try:
                for fmt in ['%Y-%m-%d', '%m/%Y', '%Y-%m', '%m-%d-%Y']:
                    try:
                        if fmt == '%m/%Y':
                            open_date = datetime.strptime(open_date_str, fmt)
                            open_date = open_date.replace(day=1)
                        else:
                            open_date = datetime.strptime(open_date_str, fmt)
                        
                        if oldest_card_date is None or open_date < oldest_card_date:
                            oldest_card_date = open_date
                        if newest_card_date is None or open_date > newest_card_date:
                            newest_card_date = open_date
                        break
                    except ValueError:
                        continue
            except:
                continue
    
    # Calculate average account age
    avg_age_months = None
    if oldest_card_date:
        total_months = (datetime.now() - oldest_card_date).days / 30.44
        avg_age_months = round(total_months, 1)
    
    return {
        "issuer_breakdown": dict(issuer_breakdown),
        "issuer_limits": dict(issuer_limits),
        "annual_fees": {
            "total": total_annual_fees,
            "fee_cards": fee_cards,
            "no_fee_cards": no_fee_cards,
            "fee_cards_count": len(fee_cards),
            "no_fee_cards_count": len(no_fee_cards)
        },
        "utilization_breakdown": sorted(utilization_breakdown, key=lambda x: x['utilization'], reverse=True),
        "age_analysis": {
            "oldest_card_date": oldest_card_date.strftime('%Y-%m-%d') if oldest_card_date else None,
            "newest_card_date": newest_card_date.strftime('%Y-%m-%d') if newest_card_date else None,
            "average_age_months": avg_age_months,
            "average_age_years": round(avg_age_months / 12, 1) if avg_age_months else None
        },
        "portfolio_stats": {
            "total_cards": len(cards),
            "active_cards": len(active_cards),
            "closed_cards": len(closed_cards),
            "unique_issuers": len(issuer_breakdown)
        }
    }


# API Routes
@api_router.get("/")
async def root():
    return {"message": "Credit Card Management API"}

@api_router.post("/upload-credit-report")
async def upload_credit_report(file: UploadFile = File(...)):
    """Upload and process a credit report PDF"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name
        
        # Extract text from PDF
        extracted_text = extract_pdf_text(tmp_path)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the PDF")
        
        # Process with OpenAI to extract credit card data
        cards_data = await parse_credit_cards_with_gpt4o(extracted_text)
        
        # Save credit cards to database
        credit_cards = []
        for card_data in cards_data:
            # Create CreditCard object with validation
            try:
                credit_card = CreditCard(
                    card_name=card_data.get('card_name', 'Unknown Card'),
                    issuer=card_data.get('issuer', 'Unknown Issuer'),
                    account_number=card_data.get('account_number', '****'),
                    open_date=card_data.get('open_date', 'Unknown'),
                    status=card_data.get('status', 'Unknown'),
                    credit_limit=card_data.get('credit_limit'),
                    current_balance=card_data.get('current_balance'),
                    annual_fee=card_data.get('annual_fee', 0)
                )
                
                # Insert into database
                await db.credit_cards.insert_one(credit_card.dict())
                credit_cards.append(credit_card.dict())
                
            except Exception as e:
                logging.warning(f"Error processing card data: {card_data}, Error: {str(e)}")
                continue
        
        # Save upload record
        upload_record = CreditReportUpload(
            filename=file.filename,
            cards_extracted=len(credit_cards),
            processing_status="Completed"
        )
        await db.credit_report_uploads.insert_one(upload_record.dict())
        
        # Clean up temporary file
        os.unlink(tmp_path)
        
        return {
            "message": "Credit report processed successfully",
            "cards_extracted": len(credit_cards),
            "credit_cards": credit_cards
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Clean up temporary file if it exists
        if 'tmp_path' in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@api_router.get("/credit-cards", response_model=List[CreditCard])
async def get_credit_cards():
    """Get all credit cards"""
    cards = await db.credit_cards.find().to_list(1000)
    return [CreditCard(**card) for card in cards]

@api_router.get("/dashboard-stats")
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        # Get all cards
        cards = await db.credit_cards.find().to_list(1000)
        
        if not cards:
            return {
                "total_cards": 0,
                "active_cards": 0,
                "closed_cards": 0,
                "average_age_years": "N/A",
                "total_credit_limit": 0,
                "total_balance": 0,
                "credit_utilization": 0,
                "total_annual_fees": 0,
                "five_24_status": {
                    "cards_in_24_months": 0,
                    "is_eligible": True,
                    "remaining_slots": 5,
                    "status": "Eligible",
                    "recommendation": "No cards found to analyze"
                },
                "portfolio_analysis": {},
                "top_utilization_cards": [],
                "issuer_breakdown": {},
                "age_analysis": {}
            }
        
        total_cards = len(cards)
        active_cards = len([card for card in cards if card.get('status', '').lower() == 'active'])
        closed_cards = total_cards - active_cards
        
        # Total credit limit and balance
        total_credit_limit = sum([card.get('credit_limit', 0) or 0 for card in cards])
        total_balance = sum([card.get('current_balance', 0) or 0 for card in cards])
        
        # Calculate 5/24 status
        five_24_status = calculate_5_24_status(cards)
        
        # Analyze portfolio
        portfolio_analysis = analyze_credit_portfolio(cards)
        
        # Get top utilization cards (for alerts)
        high_util_cards = [card for card in portfolio_analysis.get('utilization_breakdown', []) if card['utilization'] > 30]
        
        return {
            "total_cards": total_cards,
            "active_cards": active_cards,
            "closed_cards": closed_cards,
            "average_age_years": portfolio_analysis.get('age_analysis', {}).get('average_age_years', 'N/A'),
            "total_credit_limit": total_credit_limit,
            "total_balance": total_balance,
            "credit_utilization": round((total_balance / total_credit_limit * 100) if total_credit_limit > 0 else 0, 1),
            "total_annual_fees": portfolio_analysis.get('annual_fees', {}).get('total', 0),
            "five_24_status": five_24_status,
            "portfolio_analysis": portfolio_analysis,
            "top_utilization_cards": high_util_cards[:3],  # Top 3 highest utilization
            "issuer_breakdown": portfolio_analysis.get('issuer_breakdown', {}),
            "age_analysis": portfolio_analysis.get('age_analysis', {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")

@api_router.delete("/credit-cards/{card_id}")
async def delete_credit_card(card_id: str):
    """Delete a credit card"""
    result = await db.credit_cards.delete_one({"id": card_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Credit card not found")
    return {"message": "Credit card deleted successfully"}

@api_router.delete("/credit-cards")
async def clear_all_cards():
    """Clear all credit cards (for testing)"""
    await db.credit_cards.delete_many({})
    return {"message": "All credit cards cleared"}

# Legacy routes
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]


# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
