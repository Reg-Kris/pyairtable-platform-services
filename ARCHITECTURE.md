# Platform Services Architecture

## Service Consolidation Overview

### Before (Phase 3)
```
┌─────────────────────┐    ┌─────────────────────┐
│   Auth Service      │    │  Analytics Service  │
│   Port: 8000        │    │  Port: 8001         │
│   Lines: 284        │    │  Lines: 309         │
├─────────────────────┤    ├─────────────────────┤
│ POST /register      │    │ POST /events        │
│ POST /login         │    │ GET  /metrics       │
│ GET  /verify        │    │ GET  /usage/{id}    │
│ GET  /profile       │    │ GET  /costs         │
│ PUT  /profile       │    │ GET  /health        │
│ DELETE /users/{id}  │    │ POST /metrics/batch │
│ GET  /health        │    │ GET  /reports/daily │
└─────────────────────┘    └─────────────────────┘
```

### After (Phase 4A)
```
┌───────────────────────────────────────────────────────┐
│                Platform Services                      │
│                Port: 8007                            │
│                Lines: ~750                           │
├─────────────────────┬─────────────────────────────────┤
│   Auth Module       │       Analytics Module         │
├─────────────────────┼─────────────────────────────────┤
│ POST /auth/register │ POST /analytics/events          │
│ POST /auth/login    │ GET  /analytics/metrics         │
│ GET  /auth/verify   │ GET  /analytics/usage/{id}      │
│ GET  /auth/profile  │ GET  /analytics/costs           │
│ PUT  /auth/profile  │ POST /analytics/metrics/batch   │
│ DELETE /auth/users  │ GET  /analytics/reports/daily   │
└─────────────────────┴─────────────────────────────────┤
│              Legacy Compatibility Layer               │
│ POST /register → /auth/register                       │
│ POST /login → /auth/login                            │
│ POST /events → /analytics/events                     │
│ GET  /metrics → /analytics/metrics                   │
└───────────────────────────────────────────────────────┘
```

## Technical Architecture

### Application Structure
```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│                 CORS Middleware                         │
├─────────────────────────────────────────────────────────┤
│  Auth Router         │        Analytics Router         │
│  /auth/*            │        /analytics/*              │
├─────────────────────────────────────────────────────────┤
│              Legacy Endpoint Compatibility              │
│  /register, /login, /events, /metrics, etc.           │
├─────────────────────────────────────────────────────────┤
│                 Shared Database Layer                   │
│  SQLAlchemy ORM  │  Session Management                 │
├─────────────────────────────────────────────────────────┤
│   SQLite/PostgreSQL     │      Redis (Optional)        │
│   Users & Metrics       │      Caching Layer           │
└─────────────────────────────────────────────────────────┘
```

### Database Schema
```sql
-- Unified database with both auth and analytics tables

CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metrics (
    id INTEGER PRIMARY KEY,
    type VARCHAR(50) NOT NULL,           -- api_call, tool_execution, cost, session
    value REAL NOT NULL,                 -- numeric value
    user_id VARCHAR(255) NOT NULL,       -- user identifier
    metadata TEXT,                       -- JSON metadata
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_metrics_type ON metrics(type);
CREATE INDEX idx_metrics_user ON metrics(user_id);
CREATE INDEX idx_metrics_timestamp ON metrics(timestamp);
```

## API Design

### Authentication Endpoints
```yaml
/auth/register:
  POST:
    description: Register new user
    request: { email: string, password: string }
    response: { access_token: string, token_type: "bearer" }

/auth/login:
  POST:
    description: Authenticate user
    request: { email: string, password: string }
    response: { access_token: string, token_type: "bearer" }

/auth/verify:
  GET:
    description: Verify JWT token
    headers: { Authorization: "Bearer <token>" }
    response: { id: int, email: string, created_at: datetime }

/auth/profile:
  GET:
    description: Get user profile
    headers: { Authorization: "Bearer <token>" }
    response: { id: int, email: string, created_at: datetime }
  
  PUT:
    description: Update user profile
    headers: { Authorization: "Bearer <token>" }
    request: { email?: string, password?: string }
    response: { id: int, email: string, created_at: datetime }
```

### Analytics Endpoints
```yaml
/analytics/events:
  POST:
    description: Record analytics event
    request: 
      type: enum[api_call, tool_execution, cost, session]
      value: float
      user_id: string
      metadata?: object
    response: { status: "recorded", timestamp: datetime }

/analytics/metrics:
  GET:
    description: Get system metrics
    response:
      total_metrics: int
      active_users: int
      cost_per_user: float
      avg_api_calls_per_user: float
      peak_usage_hour?: int

/analytics/usage/{user_id}:
  GET:
    description: Get user usage statistics
    params: { days?: int = 7 }
    response:
      user_id: string
      days: int
      api_calls: int
      tool_executions: int
      total_cost: float
      sessions: int
      avg_session_duration?: float
      period_start: datetime
      period_end: datetime
```

## Deployment Architecture

### Container Strategy
```dockerfile
# Multi-stage build for efficiency
FROM python:3.11-slim as builder
# Install dependencies in separate stage

FROM python:3.11-slim
# Copy only necessary files
# Run as non-root user
# Health checks included
```

### Docker Compose Setup
```yaml
services:
  platform-services:
    build: .
    ports: ["8007:8007"]
    environment:
      - DATABASE_URL=sqlite:///./data/platform_services.db
      - SECRET_KEY=${SECRET_KEY}
    depends_on: [redis]
    
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
```

## Service Benefits

### Consolidation Advantages
1. **Reduced Infrastructure**: 2 services → 1 service
2. **Simplified Deployment**: Single container, single port
3. **Shared Resources**: Common database, Redis, configuration
4. **Reduced Complexity**: Unified logging, monitoring, health checks
5. **Better Performance**: Eliminate inter-service calls
6. **Cost Efficiency**: Lower resource consumption

### Performance Improvements
- **Latency**: No network calls between auth and analytics
- **Throughput**: Shared connection pools and caching
- **Resources**: Single process, shared memory
- **Scalability**: Horizontal scaling of unified service

### Operational Benefits
- **Monitoring**: Single service to monitor
- **Logging**: Unified log streams
- **Configuration**: Single configuration file
- **Health Checks**: One endpoint for service health
- **Documentation**: Consolidated API docs

## Migration Strategy

### Phase 4A Implementation
1. ✅ Create unified service structure
2. ✅ Consolidate database models
3. ✅ Implement route modules
4. ✅ Add backward compatibility
5. ✅ Create Docker configuration
6. ✅ Setup testing framework

### Deployment Steps
1. Deploy platform-services:8007
2. Update API Gateway routing
3. Test all endpoints
4. Monitor for issues
5. Deprecate old services
6. Remove old containers

### Rollback Plan
- Keep old services running during transition
- API Gateway can route to either old or new
- Database compatibility maintained
- Feature flags for gradual migration

## Security Considerations

### Authentication
- JWT tokens with configurable expiration
- Bcrypt password hashing with salt
- Bearer token validation
- User session management

### Data Protection
- SQL injection prevention (SQLAlchemy ORM)
- Input validation (Pydantic models)
- CORS configuration
- Request size limits

### Infrastructure Security
- Non-root container user
- Health check endpoints
- Environment variable configuration
- Secrets management ready

## Monitoring & Observability

### Health Checks
```json
{
  "status": "healthy",
  "database_connected": true,
  "uptime_seconds": 3600.0,
  "metrics_count": 1250,
  "users_count": 45
}
```

### Metrics Collection
- Service automatically tracks its own metrics
- Database performance monitoring
- User activity analytics
- Cost tracking and reporting
- System resource usage

### Error Handling
- Structured error responses
- Logging with correlation IDs
- Graceful degradation
- Circuit breaker patterns ready

## Future Enhancements

### Phase 4B Considerations
- WebSocket support for real-time analytics
- Advanced caching strategies
- Rate limiting implementation
- Audit logging
- Admin dashboard
- Batch processing queues

### Scalability Options
- Horizontal pod autoscaling
- Database connection pooling
- Redis clustering
- Load balancing
- CDN integration