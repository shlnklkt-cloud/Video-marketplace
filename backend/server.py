from fastapi import FastAPI, APIRouter, HTTPException, Depends, Response, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
import logging
import uuid
from pathlib import Path
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security setup
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production-please-make-it-secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

# Brute force protection
login_attempts = defaultdict(lambda: {"count": 0, "locked_until": None})

# Create the main app
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== MODELS ====================

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: str
    role: str = "user"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class VideoBase(BaseModel):
    title: str
    description: str
    video_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[str] = None
    category: str
    line_of_business: str
    key_features: Optional[List[str]] = None
    target_companies: Optional[List[str]] = None
    company_logos: Optional[List[Optional[str]]] = None
    workflow_demo_url: Optional[str] = None

class VideoCreate(VideoBase):
    pass

class Video(VideoBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ==================== AUTH UTILITIES ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(request: Request) -> User:
    """Get current user from cookie token"""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return User(**user_doc)

async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if current user is admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def check_brute_force(email: str) -> bool:
    """Check if user is locked out due to too many failed attempts"""
    attempt_data = login_attempts[email]
    
    if attempt_data["locked_until"]:
        if datetime.now(timezone.utc) < attempt_data["locked_until"]:
            return False
        else:
            # Unlock user
            attempt_data["count"] = 0
            attempt_data["locked_until"] = None
    
    return True

def record_failed_attempt(email: str):
    """Record a failed login attempt"""
    attempt_data = login_attempts[email]
    attempt_data["count"] += 1
    
    if attempt_data["count"] >= 5:
        attempt_data["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=15)

def reset_failed_attempts(email: str):
    """Reset failed attempts on successful login"""
    login_attempts[email] = {"count": 0, "locked_until": None}

# ==================== AUTH ENDPOINTS ====================

@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user"""
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_dict = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": get_password_hash(user_data.password),
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_dict)
    
    # Return user without password
    user_dict.pop("password_hash")
    user_dict["created_at"] = datetime.fromisoformat(user_dict["created_at"])
    return User(**user_dict)

@api_router.post("/auth/login")
async def login(user_data: UserLogin, response: Response):
    """Login user and set cookies"""
    # Check brute force protection
    if not check_brute_force(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Account locked for 15 minutes."
        )
    
    # Find user
    user_doc = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if not user_doc:
        record_failed_attempt(user_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user_doc["password_hash"]):
        record_failed_attempt(user_data.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Reset failed attempts on successful login
    reset_failed_attempts(user_data.email)
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user_doc["id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_refresh_token(data={"sub": user_doc["id"]})
    
    # Set cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    
    # Return user data
    user_doc.pop("password_hash")
    user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    return {"user": User(**user_doc), "message": "Login successful"}

@api_router.post("/auth/logout")
async def logout(response: Response):
    """Logout user by clearing cookies"""
    response.delete_cookie(key="access_token", secure=True, samesite="none")
    response.delete_cookie(key="refresh_token", secure=True, samesite="none")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token using refresh token"""
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found"
        )
    
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Create new access token
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Set new cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"message": "Token refreshed successfully"}

# ==================== VIDEO ENDPOINTS ====================

@api_router.get("/videos", response_model=List[Video])
async def get_videos(
    category: Optional[str] = None,
    line_of_business: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all videos with optional filters"""
    query = {}
    if category:
        query["category"] = category
    if line_of_business:
        query["line_of_business"] = line_of_business
    
    videos = await db.videos.find(query, {"_id": 0}).to_list(1000)
    
    # Convert ISO string to datetime
    for video in videos:
        if isinstance(video['created_at'], str):
            video['created_at'] = datetime.fromisoformat(video['created_at'])
    
    return videos

@api_router.get("/videos/{video_id}", response_model=Video)
async def get_video(video_id: str, current_user: User = Depends(get_current_user)):
    """Get single video by ID"""
    video = await db.videos.find_one({"id": video_id}, {"_id": 0})
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    if isinstance(video['created_at'], str):
        video['created_at'] = datetime.fromisoformat(video['created_at'])
    
    return Video(**video)

@api_router.post("/videos", response_model=Video)
async def create_video(
    video_data: VideoCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """Create a new video (admin only)"""
    video_dict = {
        "id": str(uuid.uuid4()),
        **video_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.videos.insert_one(video_dict)
    
    video_dict["created_at"] = datetime.fromisoformat(video_dict["created_at"])
    return Video(**video_dict)

@api_router.put("/videos/{video_id}", response_model=Video)
async def update_video(
    video_id: str,
    video_data: VideoCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """Update a video (admin only)"""
    video = await db.videos.find_one({"id": video_id}, {"_id": 0})
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    update_data = video_data.model_dump()
    await db.videos.update_one({"id": video_id}, {"$set": update_data})
    
    updated_video = await db.videos.find_one({"id": video_id}, {"_id": 0})
    if isinstance(updated_video['created_at'], str):
        updated_video['created_at'] = datetime.fromisoformat(updated_video['created_at'])
    
    return Video(**updated_video)

@api_router.delete("/videos/{video_id}")
async def delete_video(
    video_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a video (admin only)"""
    result = await db.videos.delete_one({"id": video_id})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    return {"message": "Video deleted successfully"}

# ==================== METADATA ENDPOINTS ====================

@api_router.get("/categories")
async def get_categories(current_user: User = Depends(get_current_user)):
    """Get all available categories"""
    categories = [
        {"id": "sales-distribution", "name": "Sales & Distribution", "sub_categories": [
            {"id": "individual-life", "name": "Individual Life"},
            {"id": "group-life", "name": "Group Life"},
            {"id": "p-and-c", "name": "P&C"},
            {"id": "broker", "name": "Broker"},
            {"id": "retirements-pension", "name": "Retirement & Pension"}
        ]},
        {"id": "pricing-underwriting", "name": "Pricing & Underwriting", "sub_categories": [
            {"id": "individual-life", "name": "Individual Life"},
            {"id": "group-life", "name": "Group Life"},
            {"id": "p-and-c", "name": "P&C"},
            {"id": "broker", "name": "Broker"},
            {"id": "retirements-pension", "name": "Retirement & Pension"}
        ]},
        {"id": "policy-servicing", "name": "Policy Servicing", "sub_categories": [
            {"id": "individual-life", "name": "Individual Life"},
            {"id": "group-life", "name": "Group Life"},
            {"id": "p-and-c", "name": "P&C"},
            {"id": "broker", "name": "Broker"},
            {"id": "retirements-pension", "name": "Retirement & Pension"}
        ]},
        {"id": "claims", "name": "Claims", "sub_categories": [
            {"id": "individual-life", "name": "Individual Life"},
            {"id": "group-life", "name": "Group Life"},
            {"id": "p-and-c", "name": "P&C"},
            {"id": "broker", "name": "Broker"},
            {"id": "retirements-pension", "name": "Retirement & Pension"}
        ]},
        {"id": "abs", "name": "ABS", "sub_categories": [
            {"id": "individual-life", "name": "Individual Life"},
            {"id": "group-life", "name": "Group Life"},
            {"id": "p-and-c", "name": "P&C"},
            {"id": "broker", "name": "Broker"},
            {"id": "retirements-pension", "name": "Retirement & Pension"}
        ]}
    ]
    return categories

@api_router.get("/lines-of-business")
async def get_lines_of_business(current_user: User = Depends(get_current_user)):
    """Get all lines of business"""
    lines = [
        {"id": "individual-life", "name": "Individual Life"},
        {"id": "group-life", "name": "Group Life"},
        {"id": "p-and-c", "name": "P&C"},
        {"id": "broker", "name": "Broker"},
        {"id": "retirements-pension", "name": "Retirement & Pension"}
    ]
    return lines

# ==================== SEED DATA ====================

@api_router.post("/seed-data")
async def seed_data():
    """Seed initial data (users and videos)"""
    # Check if data already exists
    user_count = await db.users.count_documents({})
    if user_count > 0:
        return {"message": "Data already seeded"}
    
    # Create default users
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "admin@company.com",
            "name": "Admin User",
            "password_hash": get_password_hash("Admin@123"),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "test@test.com",
            "name": "Test User",
            "password_hash": get_password_hash("test123"),
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.users.insert_many(users)
    
    # Create videos with key features and target companies
    videos = [
        {
            "id": str(uuid.uuid4()),
            "title": "Loss Run Ingestion",
            "description": "Learn about loss run ingestion processes for broker operations",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_c0rn3vk3/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "10:30",
            "category": "sales-distribution",
            "line_of_business": "broker",
            "key_features": [
                "Automated data extraction from loss run documents",
                "Integration with existing broker management systems",
                "Real-time validation and error detection",
                "Supports multiple document formats (PDF, Excel, CSV)"
            ],
            "target_companies": ["AON", "Howden", "Marsh McLennan", "Willis Towers Watson"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/y5jlqzm0_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/mbqwowk9_image.png",
                None,
                None
            ],
            "workflow_demo_url": "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0sjj7oqw_image.png",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Group UW - Census",
            "description": "Group underwriting census data analysis and processing",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_yi3rsi9k/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "12:45",
            "category": "pricing-underwriting",
            "line_of_business": "group-life",
            "key_features": [
                "AI-powered census data validation",
                "Automated risk classification",
                "Historical trend analysis",
                "Predictive pricing models"
            ],
            "target_companies": ["Canada Life", "Prudential"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/vtiwndwb_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/e5nbhzky_image.png"
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Gen AI based Risk Assessment",
            "description": "AI-powered risk assessment for P&C insurance",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_lbi6ivgw/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "15:20",
            "category": "pricing-underwriting",
            "line_of_business": "p-and-c",
            "key_features": [
                "Machine learning risk scoring",
                "Natural language processing for document analysis",
                "Real-time fraud detection",
                "Automated underwriting decisions"
            ],
            "target_companies": ["Chubb", "AXA", "SUNCORP", "Ryan", "Kemper", "Allstate", "State Farm", "Progressive"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/qoalowln_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/x3rveeo6_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0ka0792b_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/d9klqe4l_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Multi-Property Underwriting",
            "description": "Advanced multi-property underwriting techniques",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_4zs8t8ir/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "18:15",
            "category": "pricing-underwriting",
            "line_of_business": "p-and-c",
            "key_features": [
                "Portfolio risk assessment",
                "Geographic correlation analysis",
                "Catastrophe modeling integration",
                "Automated policy bundling recommendations"
            ],
            "target_companies": ["AON", "Howden", "Chubb", "AXA", "SUNCORP", "Ryan", "Kemper", "Liberty Mutual", "Travelers"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/glqv0gcm_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/q55tauu4_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/qoalowln_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/x3rveeo6_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0ka0792b_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/d9klqe4l_image.png",
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Gen AI based Risk Assessment",
            "description": "AI-driven risk assessment for broker services",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_t32t543s/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "14:30",
            "category": "pricing-underwriting",
            "line_of_business": "broker",
            "key_features": [
                "Client risk profiling",
                "Competitive market analysis",
                "Automated quote comparison",
                "Regulatory compliance checks"
            ],
            "target_companies": ["AON", "Howden", "Brown & Brown", "Hub International", "USI Insurance"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/glqv0gcm_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/q55tauu4_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Group Claims Ingestion",
            "description": "Automated group claims ingestion workflow",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_339yphko/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "11:20",
            "category": "claims",
            "line_of_business": "group-life",
            "key_features": [
                "Batch claim processing",
                "Intelligent document routing",
                "Duplicate claim detection",
                "Automated benefit calculation"
            ],
            "target_companies": ["Canada Life", "Prudential", "MetLife", "Principal Financial", "Unum"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/vtiwndwb_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/e5nbhzky_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Travel Claims",
            "description": "Processing travel insurance claims efficiently",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_ll4hrgpp/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "9:45",
            "category": "claims",
            "line_of_business": "p-and-c",
            "key_features": [
                "Multi-currency claim processing",
                "International coverage validation",
                "Medical expense verification",
                "Automated reimbursement workflows"
            ],
            "target_companies": ["Income", "Chubb", "Allianz Global", "AIG Travel", "Seven Corners"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0tw1g21j_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Auto Claims",
            "description": "Streamlined auto claims processing system",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_t257bwgm/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "13:10",
            "category": "claims",
            "line_of_business": "p-and-c",
            "key_features": [
                "Photo-based damage assessment",
                "Automated repair cost estimation",
                "Parts supplier integration",
                "Real-time claim status tracking"
            ],
            "target_companies": ["Income", "Chubb", "Geico", "USAA", "Farmers Insurance"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0tw1g21j_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Claims Co-Pilot",
            "description": "AI-assisted claims processing co-pilot for brokers",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_3pj8acoa/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "16:30",
            "category": "claims",
            "line_of_business": "broker",
            "key_features": [
                "AI-powered decision support",
                "Natural language claim summaries",
                "Automated correspondence generation",
                "Real-time adjuster assistance"
            ],
            "target_companies": ["Arthur J. Gallagher", "Lockton", "AssuredPartners"],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "ABS Life",
            "description": "Automated Business Services for Individual Life Insurance",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_d30zkx7q/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "14:00",
            "category": "abs",
            "line_of_business": "individual-life",
            "key_features": [
                "End-to-end policy administration automation",
                "Intelligent underwriting workflows",
                "Self-service customer portal",
                "Real-time policy updates and modifications"
            ],
            "target_companies": ["Canada Life", "Prudential", "Achmea"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/y321voku_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/fyq7gj4z_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/mq08kluw_image.png"
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "ABS P&C",
            "description": "Automated Business Services for Property & Casualty Insurance",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_m10ra3lp/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "16:45",
            "category": "abs",
            "line_of_business": "p-and-c",
            "key_features": [
                "Automated policy issuance and renewals",
                "Digital document management",
                "Integration with carrier systems",
                "Advanced reporting and analytics"
            ],
            "target_companies": ["CNA", "MSIG", "AON"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/xt48o0at_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/i6qo09d3_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/spi7cs6o_image.png"
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Participant Onboarding",
            "description": "Streamlined participant onboarding for retirement plans",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_ncffnye4/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "11:30",
            "category": "sales-distribution",
            "line_of_business": "retirements-pension",
            "key_features": [
                "Digital enrollment workflows",
                "Automated eligibility verification",
                "Multi-plan selection interface",
                "Personalized investment recommendations"
            ],
            "target_companies": ["Achmea", "Fidelity", "Vanguard", "T. Rowe Price"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/lddy54k0_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Scheme Administration",
            "description": "Comprehensive pension scheme administration platform",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_zo65j4yy/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "19:20",
            "category": "pricing-underwriting",
            "line_of_business": "retirements-pension",
            "key_features": [
                "Automated contribution processing",
                "Regulatory compliance monitoring",
                "Member communication portal",
                "Investment performance tracking"
            ],
            "target_companies": ["Achmea", "Aon Hewitt", "Mercer", "Willis Towers Watson"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/lddy54k0_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Invoicing & Collection",
            "description": "Automated invoicing and premium collection system",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_dyhjv5pg/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "10:15",
            "category": "pricing-underwriting",
            "line_of_business": "retirements-pension",
            "key_features": [
                "Automated billing generation",
                "Multiple payment method support",
                "Dunning management",
                "Revenue reconciliation"
            ],
            "target_companies": ["Achmea", "Empower Retirement", "TIAA", "Prudential Retirement"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/lddy54k0_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "RAG based Conversational Agent",
            "description": "Retrieval-Augmented Generation chatbot for policy servicing",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_mf97xtza/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "13:50",
            "category": "policy-servicing",
            "line_of_business": "p-and-c",
            "key_features": [
                "Natural language policy queries",
                "Context-aware responses",
                "Multi-document search",
                "24/7 automated customer support"
            ],
            "target_companies": ["AON", "Howden", "Canada Life", "Prudential", "Achmea", "Chubb", "AXA", "SUNCORP", "Ryan", "Kemper", "Liberty Mutual", "Farmers Insurance", "American Family"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/glqv0gcm_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/q55tauu4_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/vtiwndwb_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/e5nbhzky_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/mq08kluw_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/qoalowln_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/x3rveeo6_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0ka0792b_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/d9klqe4l_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Claims Ingestion & JSON Extraction",
            "description": "Intelligent claims data extraction and structuring",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_fno288jd/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "12:30",
            "category": "claims",
            "line_of_business": "p-and-c",
            "key_features": [
                "OCR and document parsing",
                "Structured data extraction",
                "Multi-format support (PDF, images, forms)",
                "Validation and quality checks"
            ],
            "target_companies": ["AON", "Howden", "Canada Life", "Prudential", "Achmea", "Chubb", "AXA", "SUNCORP", "Ryan", "Kemper", "State Farm", "Progressive", "Allstate"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/glqv0gcm_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/q55tauu4_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/vtiwndwb_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/e5nbhzky_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/mq08kluw_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/nwh4ue8x_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/qoalowln_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/x3rveeo6_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/0ka0792b_image.png",
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/d9klqe4l_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "title": "Payout (Disbursement)",
            "description": "Automated retirement benefit payout processing",
            "video_url": "https://mediaexchange.accenture.com/embed/secure/iframe/entryId/1_imczy83m/uiConfId/54057682/st/0",
            "thumbnail_url": None,
            "duration": "15:40",
            "category": "claims",
            "line_of_business": "retirements-pension",
            "key_features": [
                "Tax withholding calculations",
                "Multiple disbursement options",
                "Regulatory reporting",
                "Audit trail and compliance tracking"
            ],
            "target_companies": ["Achmea", "Principal Financial", "Lincoln Financial", "Nationwide Retirement"],
            "company_logos": [
                "https://customer-assets.emergentagent.com/job_ai-marketplace-demo/artifacts/lddy54k0_image.png",
                None,
                None,
                None
            ],
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.videos.insert_many(videos)
    
    return {"message": "Data seeded successfully", "users": len(users), "videos": len(videos)}

# ==================== ROOT ENDPOINT ====================

@api_router.get("/")
async def root():
    return {"message": "Agentic Market Place API", "version": "1.0.0"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
