"""
Platform Services Configuration
Unified configuration for Auth & Analytics services
"""

import os
from typing import Optional

class Settings:
    """Application configuration"""
    
    # Service Configuration
    SERVICE_NAME: str = "platform-services"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8007
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    API_KEY: str = os.getenv("API_KEY", "default-api-key-change-in-production")
    REQUIRE_API_KEY: bool = os.getenv("REQUIRE_API_KEY", "true").lower() == "true"
    
    # JWT Configuration (Auth Service)
    JWT_SECRET: str = os.getenv("JWT_SECRET", "default-jwt-secret-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRES_IN: str = os.getenv("JWT_EXPIRES_IN", "24h")
    
    # Database Configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://admin:changeme@localhost:5432/pyairtablemcp"
    )
    
    # Redis Configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # CORS Settings
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # Auth Service Settings
    PASSWORD_MIN_LENGTH: int = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
    PASSWORD_HASH_ROUNDS: int = int(os.getenv("PASSWORD_HASH_ROUNDS", "12"))
    
    # Analytics Service Settings
    ANALYTICS_RETENTION_DAYS: int = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))
    METRICS_BATCH_SIZE: int = int(os.getenv("METRICS_BATCH_SIZE", "100"))
    
    # External Service URLs (for analytics data collection)
    AUTH_SERVICE_URL: str = os.getenv("AUTH_SERVICE_URL", "http://localhost:8007")
    
    @property
    def redis_url_with_password(self) -> str:
        """Get Redis URL with password if configured"""
        if self.REDIS_PASSWORD:
            # Parse and rebuild URL with password
            from urllib.parse import urlparse, urlunparse
            parsed = urlparse(self.REDIS_URL)
            
            # Add password to netloc
            netloc = f":{self.REDIS_PASSWORD}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            
            return urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        return self.REDIS_URL
    
    @property
    def jwt_expires_seconds(self) -> int:
        """Convert JWT expiration to seconds"""
        expires_str = self.JWT_EXPIRES_IN.lower()
        
        if expires_str.endswith('h'):
            return int(expires_str[:-1]) * 3600
        elif expires_str.endswith('d'):
            return int(expires_str[:-1]) * 86400
        elif expires_str.endswith('m'):
            return int(expires_str[:-1]) * 60
        else:
            # Default to seconds if no unit specified
            return int(expires_str)
    
    def validate(self) -> bool:
        """Validate configuration"""
        issues = []
        
        # Security validation
        if self.ENVIRONMENT == "production":
            if self.API_KEY == "default-api-key-change-in-production":
                issues.append("API_KEY must be changed in production")
            
            if self.JWT_SECRET == "default-jwt-secret-change-in-production":
                issues.append("JWT_SECRET must be changed in production")
            
            if "changeme" in self.DATABASE_URL:
                issues.append("DATABASE_URL contains default password")
        
        # Database validation
        if not self.DATABASE_URL.startswith("postgresql://"):
            issues.append("DATABASE_URL must be a PostgreSQL connection string")
        
        # Redis validation
        if not self.REDIS_URL.startswith("redis://"):
            issues.append("REDIS_URL must be a Redis connection string")
        
        if issues:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("Configuration validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False
        
        return True

# Global settings instance
settings = Settings()

# Validate on import
if not settings.validate():
    if settings.ENVIRONMENT == "production":
        raise ValueError("Invalid production configuration")
    else:
        import logging
        logging.getLogger(__name__).warning("Configuration issues detected in development mode")