"""
PyAirtable Platform Services - Unified Auth & Analytics
Consolidates authentication and analytics services into a single microservice
Port: 8007, Routes: /auth/* and /analytics/*
"""

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import uvicorn
import logging
import time
from typing import Optional

# Route modules
from routes.auth import router as auth_router
from routes.analytics import router as analytics_router
from config import settings
from database import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting PyAirtable Platform Services")
    await init_db()
    logger.info("✅ Database initialized")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Platform Services")
    await close_db()
    logger.info("✅ Cleanup completed")

# Create FastAPI app
app = FastAPI(
    title="PyAirtable Platform Services",
    description="Unified Authentication & Analytics Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Security middlewares
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response

# API key validation
async def verify_api_key(request: Request) -> Optional[str]:
    """Verify API key from header"""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None
    
    # Constant-time comparison to prevent timing attacks
    import hmac
    expected = settings.API_KEY.encode()
    provided = api_key.encode()
    
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return api_key

# Health check endpoint
@app.get("/health")
async def health_check():
    """Combined health check for platform services"""
    try:
        from database import get_health_status
        db_status = await get_health_status()
        
        return {
            "status": "healthy",
            "service": "platform-services",
            "version": "1.0.0",
            "components": {
                "auth": {"status": "healthy", "port": 8007},
                "analytics": {"status": "healthy", "port": 8007},
                "database": db_status,
                "redis": {"status": "healthy"}  # TODO: Add Redis health check
            },
            "endpoints": {
                "auth": ["/auth/register", "/auth/login", "/auth/verify", "/auth/profile"],
                "analytics": ["/analytics/events", "/analytics/metrics", "/analytics/usage", "/analytics/costs"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Include routers
app.include_router(
    auth_router,
    prefix="/auth",
    tags=["Authentication"],
    dependencies=[Depends(verify_api_key)] if settings.REQUIRE_API_KEY else []
)

app.include_router(
    analytics_router,
    prefix="/analytics", 
    tags=["Analytics"],
    dependencies=[Depends(verify_api_key)] if settings.REQUIRE_API_KEY else []
)

# Legacy endpoint compatibility (backward compatibility)
from routes.auth import register, login, verify_token, get_profile, update_profile, delete_user
from routes.analytics import track_event, get_metrics, get_user_usage, get_costs

# Legacy auth endpoints (deprecated but supported)
app.post("/register", deprecated=True)(register)
app.post("/login", deprecated=True)(login)  
app.get("/verify", deprecated=True)(verify_token)
app.get("/profile", deprecated=True)(get_profile)
app.put("/profile", deprecated=True)(update_profile)

# Legacy analytics endpoints (deprecated but supported)
app.post("/events", deprecated=True)(track_event)
app.get("/metrics", deprecated=True)(get_metrics)
app.get("/usage/{user_id}", deprecated=True)(get_user_usage)
app.get("/costs", deprecated=True)(get_costs)

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8007,
        log_level=settings.LOG_LEVEL.lower(),
        reload=settings.ENVIRONMENT == "development"
    )