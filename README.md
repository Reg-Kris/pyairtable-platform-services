# PyAirtable Platform Services

Unified microservice consolidating Authentication and Analytics services for the PyAirtable ecosystem.

## 🎯 Service Overview

**Platform Services** combines two previously separate microservices:
- **Authentication Service**: JWT-based user authentication and management
- **Analytics Service**: Event tracking, metrics collection, and usage analytics

**Port**: `8007` | **Architecture**: FastAPI + PostgreSQL + Redis

## 🚀 Quick Start

### Docker Compose (Recommended)
```bash
# In the main pyairtable-compose directory
docker-compose up platform-services -d

# Check health
curl http://localhost:8007/health
```

### Local Development
```bash
# Clone and setup
git clone <repository-url>
cd pyairtable-platform-services

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn main:app --host 0.0.0.0 --port 8007 --reload
```

## 📚 API Documentation

### Authentication Endpoints (`/auth/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | User registration |
| POST | `/auth/login` | User authentication |
| GET | `/auth/verify` | JWT token verification |
| GET | `/auth/profile` | Get user profile |
| PUT | `/auth/profile` | Update user profile |
| DELETE | `/auth/users/{id}` | Delete user account |

### Analytics Endpoints (`/analytics/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/analytics/events` | Track events |
| POST | `/analytics/metrics` | Create metrics |
| POST | `/analytics/metrics/batch` | Batch create metrics |
| GET | `/analytics/metrics` | Get metrics (filtered) |
| GET | `/analytics/usage/{user_id}` | User usage stats |
| GET | `/analytics/costs` | Cost breakdown |
| GET | `/analytics/dashboard` | Dashboard metrics |

### Legacy Endpoints (Backward Compatibility)

The service maintains backward compatibility with the original separate services:

```bash
# Legacy auth endpoints (deprecated but supported)
POST /register → /auth/register
POST /login → /auth/login
GET /verify → /auth/verify
GET /profile → /auth/profile
PUT /profile → /auth/profile

# Legacy analytics endpoints (deprecated but supported)
POST /events → /analytics/events
GET /metrics → /analytics/metrics
GET /usage/{user_id} → /analytics/usage/{user_id}
GET /costs → /analytics/costs
```

## 🔧 Configuration

### Environment Variables

```bash
# Service Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
PORT=8007

# Security
API_KEY=your-secure-api-key
REQUIRE_API_KEY=true

# JWT Authentication
JWT_SECRET=your-jwt-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=24h

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/database

# Redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# Auth Settings
PASSWORD_MIN_LENGTH=8
PASSWORD_HASH_ROUNDS=12

# Analytics Settings
ANALYTICS_RETENTION_DAYS=90
METRICS_BATCH_SIZE=100
```

## 🏗️ Architecture

### Database Schema

```sql
-- Users (Authentication)
platform_users:
  - id (primary key)
  - email (unique)
  - password_hash
  - first_name, last_name
  - is_active
  - created_at, updated_at
  - meta_data (JSON)

-- Analytics Events
platform_analytics_events:
  - id (primary key)
  - user_id (optional)
  - event_type
  - event_data (JSON)
  - session_id, ip_address, user_agent
  - timestamp

-- Analytics Metrics
platform_analytics_metrics:
  - id (primary key)
  - metric_name, metric_value, metric_type
  - user_id, service_name, endpoint
  - labels (JSON)
  - timestamp

-- Usage Tracking
platform_analytics_usage:
  - id (primary key)
  - user_id
  - api_calls_count, tokens_used, cost_usd
  - date, period_type
  - created_at, updated_at
```

### Service Integration

```mermatch
graph TB
    Client[Frontend/API Client]
    Gateway[API Gateway]
    Platform[Platform Services]
    DB[(PostgreSQL)]
    Cache[(Redis)]
    
    Client -->|HTTP/JWT| Gateway
    Gateway -->|/auth/*, /analytics/*| Platform
    Platform -->|Query/Store| DB
    Platform -->|Cache/Sessions| Cache
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8007/health
```

### Authentication Flow
```bash
# Register user
curl -X POST http://localhost:8007/auth/register \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Login
curl -X POST http://localhost:8007/auth/login \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'

# Use JWT token
curl http://localhost:8007/auth/profile \
  -H "Authorization: Bearer your-jwt-token" \
  -H "X-API-Key: your-api-key"
```

### Analytics Usage
```bash
# Track event
curl -X POST http://localhost:8007/analytics/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "event_type": "user_login",
    "user_id": 1,
    "event_data": {"source": "web"}
  }'

# Create metric
curl -X POST http://localhost:8007/analytics/metrics \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "metric_name": "api_calls",
    "metric_value": 1,
    "metric_type": "counter",
    "service_name": "platform-services",
    "endpoint": "/auth/login"
  }'
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt with configurable rounds
- **API Key Validation**: Constant-time comparison to prevent timing attacks
- **CORS Configuration**: Configurable origin restrictions
- **Rate Limiting**: Built-in request limiting (via API Gateway)
- **Input Validation**: Pydantic model validation
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

## 📊 Monitoring & Observability

### Health Check Response
```json
{
  "status": "healthy",
  "service": "platform-services",
  "version": "1.0.0",
  "components": {
    "auth": {"status": "healthy", "port": 8007},
    "analytics": {"status": "healthy", "port": 8007},
    "database": {"status": "healthy", "connection": "active"},
    "redis": {"status": "healthy"}
  },
  "endpoints": {
    "auth": ["/auth/register", "/auth/login", "/auth/verify", "/auth/profile"],
    "analytics": ["/analytics/events", "/analytics/metrics", "/analytics/usage", "/analytics/costs"]
  }
}
```

### Logging
- Structured logging with request/response tracking
- Authentication events logging
- Error tracking and monitoring
- Performance metrics (request duration)

## 🚀 Deployment

### Docker Compose Integration
The service is designed to work seamlessly with the main PyAirtable docker-compose setup:

```yaml
services:
  platform-services:
    build: ../pyairtable-platform-services
    ports:
      - "8007:8007"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
      - REDIS_URL=redis://redis:6379
      - API_KEY=${API_KEY}
    depends_on:
      - postgres
      - redis
```

### Production Considerations
- Use strong, unique JWT secrets and API keys
- Configure proper CORS origins (no wildcards)
- Set up database connection pooling
- Enable Redis authentication and SSL
- Configure log aggregation
- Set up monitoring and alerting

## 📈 Consolidation Benefits

**Before**: 2 separate services (Auth + Analytics)
**After**: 1 unified service

### Resource Efficiency
- 50% reduction in container overhead
- Shared database connections and Redis client
- Unified configuration management
- Single health check endpoint

### Operational Simplicity
- One service to deploy, monitor, and maintain
- Consolidated logging and error handling
- Shared middleware and security policies
- Simplified service discovery

### Performance Improvements
- Eliminates inter-service HTTP calls
- Shared in-memory caching
- Reduced network latency
- Optimized database queries

## 🛠️ Development

### Project Structure
```
pyairtable-platform-services/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── database.py            # Database models and connection
├── routes/
│   ├── auth.py            # Authentication endpoints
│   └── analytics.py       # Analytics endpoints
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container configuration
└── README.md             # This file
```

### Code Quality
- Type hints throughout codebase
- Async/await for all I/O operations
- Comprehensive error handling
- Pydantic models for request/response validation
- SQLAlchemy ORM for database operations

---

**Service Status**: ✅ Production Ready  
**Port**: `8007`  
**Replaces**: `auth-service` (8007) + `analytics-service` (8005)  
**Backward Compatible**: Yes (legacy endpoints supported)