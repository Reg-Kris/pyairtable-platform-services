"""
Unified data models for platform services (auth + analytics).
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Database setup
Base = declarative_base()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# === SQLAlchemy Models ===

class User(Base):
    """SQLAlchemy User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MetricRecord(Base):
    """SQLAlchemy Metric model."""
    __tablename__ = "metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    user_id = Column(String(255), nullable=False, index=True)
    metadata = Column(Text)  # JSON string
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

# === Pydantic Models - Auth ===

class UserCreate(BaseModel):
    """Pydantic model for user creation."""
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    """Pydantic model for user updates."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    """Pydantic model for user response."""
    id: int
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    """Pydantic model for JWT token response."""
    access_token: str
    token_type: str = "bearer"

# === Pydantic Models - Analytics ===

class MetricType(str, Enum):
    """Supported metric types."""
    API_CALL = "api_call"
    TOOL_EXECUTION = "tool_execution"
    COST = "cost"
    SESSION = "session"

class MetricRequest(BaseModel):
    """Request model for recording metrics."""
    type: MetricType
    value: float
    user_id: str
    metadata: Optional[Dict[str, Any]] = None

class Metric(BaseModel):
    """Core metric model."""
    id: Optional[int] = None
    type: MetricType
    value: float
    user_id: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class UserStats(BaseModel):
    """User statistics model."""
    user_id: str
    days: int
    api_calls: int = 0
    tool_executions: int = 0
    total_cost: float = 0.0
    sessions: int = 0
    avg_session_duration: Optional[float] = None
    period_start: datetime
    period_end: datetime

class SystemMetrics(BaseModel):
    """System-wide metrics aggregation."""
    total_metrics: int
    active_users: int
    cost_per_user: float
    avg_api_calls_per_user: float
    peak_usage_hour: Optional[int] = None

class DailyReport(BaseModel):
    """Daily system report model."""
    date: str
    total_users: int
    total_api_calls: int
    total_tool_executions: int
    total_cost: float
    total_sessions: int
    top_users: list[Dict[str, Any]]

class HealthStatus(BaseModel):
    """Service health status."""
    status: str = "healthy"
    database_connected: bool = True
    uptime_seconds: float
    metrics_count: int = 0
    users_count: int = 0
    last_metric_time: Optional[datetime] = None

# === Utility Functions ===

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password."""
    return pwd_context.verify(plain_password, hashed_password)

# === Database Setup Function ===

def create_database_session(database_url: str):
    """Create database engine and session."""
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    return engine, SessionLocal