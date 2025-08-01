"""
Authentication routes for Platform Services
JWT-based authentication with user management
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import bcrypt
import jwt
import logging
from datetime import datetime, timedelta

from database import get_db, User
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True

class UserResponse(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse

# Auth utilities
def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt(rounds=settings.PASSWORD_HASH_ROUNDS)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user: User) -> str:
    """Create JWT token for user"""
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=settings.jwt_expires_seconds),
        "type": "access"
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        
        # Decode JWT token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail="Authentication failed")

# Auth endpoints
@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user"""
    try:
        # Validate password length
        if len(user_data.password) < settings.PASSWORD_MIN_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
            )
        
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = hash_password(user_data.password)
        user = User(
            email=user_data.email,
            password_hash=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Create JWT token
        token = create_jwt_token(user)
        
        logger.info(f"User registered: {user.email}")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_expires_seconds,
            user=UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    try:
        # Get user by email
        result = await db.execute(select(User).where(User.email == credentials.email))
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Verify password
        if not verify_password(credentials.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Create JWT token
        token = create_jwt_token(user)
        
        logger.info(f"User logged in: {user.email}")
        
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_expires_seconds,
            user=UserResponse(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                created_at=user.created_at
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/verify")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify JWT token and return user info"""
    return {
        "valid": True,
        "user": UserResponse(
            id=current_user.id,
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )
    }

@router.get("/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserProfile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    try:
        # Update user fields
        current_user.first_name = profile_data.first_name
        current_user.last_name = profile_data.last_name
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(current_user)
        
        logger.info(f"Profile updated: {current_user.email}")
        
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            first_name=current_user.first_name,
            last_name=current_user.last_name,
            is_active=current_user.is_active,
            created_at=current_user.created_at
        )
        
    except Exception as e:
        logger.error(f"Profile update error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Profile update failed")

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user (admin only or self-deletion)"""
    try:
        # For now, only allow self-deletion
        if current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Can only delete your own account")
        
        # Soft delete by setting is_active to False
        current_user.is_active = False
        current_user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(f"User deleted: {current_user.email}")
        
        return {"message": "User account deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User deletion error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="User deletion failed")