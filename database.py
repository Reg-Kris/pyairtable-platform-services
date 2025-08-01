"""
Database configuration and connection management
Unified database for Auth & Analytics services
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import text
from sqlalchemy import String, DateTime, Integer, Text, Boolean, JSON
from datetime import datetime
from typing import AsyncGenerator, Dict, Any
import logging

from config import settings

logger = logging.getLogger(__name__)

# Database engine and session
engine = None
async_session_maker = None

class Base(DeclarativeBase):
    """Base model class"""
    pass

# Auth Models
class User(Base):
    """User model for authentication"""
    __tablename__ = "platform_users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile information
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

# Analytics Models
class AnalyticsEvent(Base):
    """Analytics event model"""
    __tablename__ = "platform_analytics_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)  # Can be anonymous
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Contextual information
    session_id: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)

class AnalyticsMetric(Base):
    """Analytics metrics aggregation"""
    __tablename__ = "platform_analytics_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[float] = mapped_column(nullable=False)
    metric_type: Mapped[str] = mapped_column(String(50), nullable=False)  # counter, gauge, histogram
    
    # Dimensions
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    service_name: Mapped[str] = mapped_column(String(100), nullable=True)
    endpoint: Mapped[str] = mapped_column(String(255), nullable=True)
    
    # Metadata
    labels: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AnalyticsUsage(Base):
    """User usage tracking"""
    __tablename__ = "platform_analytics_usage"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Usage metrics
    api_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    
    # Time period
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), default="daily")  # daily, monthly
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

async def init_db():
    """Initialize database connection and create tables"""
    global engine, async_session_maker
    
    try:
        # Convert sync PostgreSQL URL to async
        database_url = settings.DATABASE_URL
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Create async engine
        engine = create_async_engine(
            database_url,
            echo=settings.LOG_LEVEL == "DEBUG",
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        
        # Create session maker
        async_session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        raise

async def close_db():
    """Close database connections"""
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("✅ Database connections closed")

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session"""
    if not async_session_maker:
        raise RuntimeError("Database not initialized")
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_health_status() -> Dict[str, Any]:
    """Get database health status"""
    if not engine:
        return {"status": "unhealthy", "error": "Database not initialized"}
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
        
        return {
            "status": "healthy",
            "connection": "active",
            "pool_size": engine.pool.size(),
            "checked_out": engine.pool.checkedout()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Redis connection (for caching and sessions)
redis_client = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    try:
        import redis.asyncio as redis
        
        redis_client = redis.from_url(
            settings.redis_url_with_password,
            encoding="utf-8",
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("✅ Redis initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Redis initialization failed: {str(e)}")
        # Don't raise - Redis is optional for basic functionality
        redis_client = None

async def get_redis():
    """Get Redis client"""
    if not redis_client:
        await init_redis()
    return redis_client