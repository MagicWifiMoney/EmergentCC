from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
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
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from jose import JWTError, jwt
import secrets
import hashlib


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI client
openai_client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Create the main app
app = FastAPI()

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET)

# OAuth Configuration
config = Config()
oauth = OAuth()

# Get the current preview URL for redirect
import os
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://b24cc02b-55f7-4d08-a4fd-c74e2c6f2cd5.preview.emergentagent.com')

oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
    authorize_redirect_uri=f"{FRONTEND_URL}/api/auth/google"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Auth router (also needs /api prefix for ingress routing)
auth_router = APIRouter(prefix="/api")


# Define Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime = Field(default_factory=datetime.utcnow)

class CreditCard(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Associate cards with users
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
    user_id: str  # Associate uploads with users
    filename: str
    upload_date: datetime = Field(default_factory=datetime.utcnow)
    cards_extracted: int
    processing_status: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None


# Utility Functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request) -> User:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from Authorization header first
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    else:
        # Fallback to cookie
        token = request.cookies.get("access_token")
    
    if not token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user_dict = await db.users.find_one({"email": token_data.email})
    if user_dict is None:
        raise credentials_exception
    
    return User(**user_dict)

async def get_current_user_optional(request: Request) -> Optional[User]:
    """Optional authentication - returns None if not authenticated"""
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


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


# Authentication Routes
@auth_router.get("/login/google")
async def google_login(request: Request):
    redirect_uri = f"{FRONTEND_URL}/api/auth/google"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@auth_router.get("/auth/google")
async def google_auth(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info from Google")
        
        # Create or update user in database
        user_data = {
            "email": user_info.get('email'),
            "name": user_info.get('name'),
            "picture": user_info.get('picture'),
            "last_login": datetime.utcnow()
        }
        
        # Update or create user
        existing_user = await db.users.find_one({"email": user_data["email"]})
        if existing_user:
            await db.users.update_one(
                {"email": user_data["email"]},
                {"$set": user_data}
            )
            user_id = existing_user["id"]
        else:
            user_data["id"] = str(uuid.uuid4())
            user_data["created_at"] = datetime.utcnow()
            await db.users.insert_one(user_data)
            user_id = user_data["id"]
        
        # Create tokens
        access_token = create_access_token(data={"sub": user_data["email"]})
        refresh_token = create_refresh_token(data={"sub": user_data["email"]})
        
        # Create response and set cookies
        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token", 
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")

@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")
    return {"message": "Successfully logged out"}

@auth_router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        picture=current_user.picture
    )

@auth_router.post("/refresh")
async def refresh_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    
    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Create new access token
    access_token = create_access_token(data={"sub": email})
    
    response = JSONResponse(content={"message": "Token refreshed"})
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=True,
        samesite="lax"
    )
    return response


# API Routes (Protected)
@api_router.get("/")
async def root():
    return {"message": "Credit Card Management API"}

@api_router.post("/upload-credit-report")
async def upload_credit_report(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
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
        
        # Save credit cards to database with user association
        credit_cards = []
        for card_data in cards_data:
            # Create CreditCard object with validation
            try:
                credit_card = CreditCard(
                    user_id=current_user.id,  # Associate with current user
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
            user_id=current_user.id,  # Associate with current user
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
async def get_credit_cards(current_user: User = Depends(get_current_user)):
    """Get current user's credit cards"""
    cards = await db.credit_cards.find({"user_id": current_user.id}).to_list(1000)
    return [CreditCard(**card) for card in cards]

@api_router.post("/credit-cards", response_model=CreditCard)
async def create_credit_card(card: CreditCard, current_user: User = Depends(get_current_user)):
    """Create a new credit card (for testing purposes)"""
    try:
        # Generate new ID if not provided and associate with current user
        if not card.id:
            card.id = str(uuid.uuid4())
        card.user_id = current_user.id
        
        # Insert into database
        await db.credit_cards.insert_one(card.dict())
        return card
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating credit card: {str(e)}")

@api_router.get("/dashboard-stats")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get comprehensive dashboard statistics for current user"""
    try:
        # Get current user's cards only
        cards = await db.credit_cards.find({"user_id": current_user.id}).to_list(1000)
        
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
                    "recommendation": "No cards found to analyze",
                    "recent_cards": []
                },
                "portfolio_analysis": {
                    "issuer_breakdown": {},
                    "issuer_limits": {},
                    "annual_fees": {
                        "total": 0,
                        "fee_cards": [],
                        "no_fee_cards": [],
                        "fee_cards_count": 0,
                        "no_fee_cards_count": 0
                    },
                    "utilization_breakdown": [],
                    "age_analysis": {
                        "oldest_card_date": None,
                        "newest_card_date": None,
                        "average_age_months": None,
                        "average_age_years": None
                    },
                    "portfolio_stats": {
                        "total_cards": 0,
                        "active_cards": 0,
                        "closed_cards": 0,
                        "unique_issuers": 0
                    }
                },
                "top_utilization_cards": [],
                "issuer_breakdown": {},
                "age_analysis": {
                    "oldest_card_date": None,
                    "newest_card_date": None,
                    "average_age_months": None,
                    "average_age_years": None
                }
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
async def delete_credit_card(card_id: str, current_user: User = Depends(get_current_user)):
    """Delete a credit card (only user's own cards)"""
    result = await db.credit_cards.delete_one({"id": card_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Credit card not found")
    return {"message": "Credit card deleted successfully"}

@api_router.delete("/credit-cards")
async def clear_all_cards(current_user: User = Depends(get_current_user)):
    """Clear all credit cards for current user"""
    await db.credit_cards.delete_many({"user_id": current_user.id})
    return {"message": "All credit cards cleared"}


# Include routers
app.include_router(auth_router)
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
