# Platform Services - Claude Context

## 🎯 Service Purpose
This is the **unified platform services** of the PyAirtable ecosystem - consolidating authentication and analytics functionality into a single, efficient microservice. It handles JWT-based user authentication, event tracking, metrics collection, and usage analytics.

## 🏗️ Current State

### Deployment Status
- **Environment**: ✅ Local Kubernetes (Minikube)
- **Services Running**: ✅ 7 out of 9 services operational
- **Database Analysis**: ✅ Airtable test database analyzed (34 tables, 539 fields)
- **Metadata Tool**: ✅ Table analysis tool executed successfully

### Service Status
- **Authentication**: ✅ JWT-based user authentication and management
- **Analytics**: ✅ Event tracking, metrics collection, and usage analytics
- **Database**: ✅ PostgreSQL with SQLAlchemy ORM
- **Caching**: ✅ Redis for session management
- **API Documentation**: ✅ Comprehensive REST API endpoints
- **Security**: ✅ bcrypt password hashing, JWT tokens, API key validation
- **Testing**: ⚠️ Basic health checks, needs comprehensive test suite

### Recent Fixes Applied
- ✅ Pydantic v2 compatibility issues resolved
- ✅ Gemini ThinkingConfig configuration fixed
- ✅ SQLAlchemy metadata handling updated
- ✅ Service deployment to Kubernetes completed

## 🛠️ API Endpoints

### Authentication Routes (/auth/*)
```python
POST   /auth/register    # User registration
POST   /auth/login       # User authentication
GET    /auth/verify      # JWT token verification
GET    /auth/profile     # Get user profile
PUT    /auth/profile     # Update user profile
DELETE /auth/users/{id}  # Delete user account
```

### Analytics Routes (/analytics/*)
```python
POST /analytics/events              # Track events
POST /analytics/metrics             # Create metrics
POST /analytics/metrics/batch       # Batch create metrics
GET  /analytics/metrics             # Get metrics (filtered)
GET  /analytics/usage/{user_id}     # User usage stats
GET  /analytics/costs               # Cost breakdown
GET  /analytics/dashboard           # Dashboard metrics
```

### System Routes
```python
GET  /health                        # Health check with component status
```

## 🚀 Immediate Priorities

1. **Comprehensive Testing** (HIGH)
   ```python
   # Priority test coverage:
   - Authentication flow tests (register, login, verify)
   - Analytics event tracking tests
   - JWT token validation tests
   - Database integration tests
   - Error handling tests
   ```

2. **Enhanced Monitoring** (MEDIUM)
   ```python
   # Add monitoring metrics:
   platform_auth_requests_total{method,endpoint}
   platform_analytics_events_total{event_type}
   platform_jwt_tokens_issued_total
   platform_database_connections_active
   ```

3. **Performance Optimization** (MEDIUM)
   ```python
   # Database connection pooling
   # Redis connection optimization
   # Response caching for frequent queries
   ```

## 🔮 Future Enhancements

### Phase 1 (Next Sprint)
- [ ] Comprehensive test suite with pytest
- [ ] Enhanced error handling and logging
- [ ] Performance metrics and monitoring
- [ ] Database migration scripts

### Phase 2 (Next Month)
- [ ] Advanced analytics dashboards
- [ ] User role-based access control
- [ ] API rate limiting per user
- [ ] Event streaming for real-time analytics

### Phase 3 (Future)
- [ ] Multi-tenant support
- [ ] Advanced user management features
- [ ] Analytics data visualization
- [ ] Integration with external analytics platforms

## ⚠️ Known Issues
1. **Limited test coverage** - Needs comprehensive testing
2. **Basic error handling** - Could be more granular
3. **No user roles** - All authenticated users have same permissions
4. **Missing audit logging** - Authentication events need better tracking

## 🧪 Testing Strategy
```python
# Priority test coverage:
- Unit tests for all authentication flows
- Integration tests with PostgreSQL and Redis
- API endpoint testing with FastAPI TestClient
- Security testing for JWT handling
- Performance testing for concurrent users
```

## 🔧 Technical Details
- **Framework**: FastAPI with async/await
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for session management
- **Authentication**: JWT tokens with bcrypt password hashing
- **Python**: 3.12
- **Port**: 8007

## 📊 Performance Targets
- **Response Time**: < 100ms for auth operations
- **Throughput**: 1000+ requests/second
- **JWT Generation**: < 50ms
- **Database Queries**: < 20ms average
- **Memory Usage**: < 200MB

## 🤝 Service Dependencies
```
Frontend → API Gateway → Platform Services → PostgreSQL
                              ↓
                           Redis Cache
```

## 💡 Development Tips
1. Use JWT tokens for all authenticated requests
2. Track all user interactions via analytics events
3. Cache frequently accessed user data in Redis
4. Use database transactions for critical operations

## 🚨 Critical Configuration
```python
# Required environment variables:
JWT_SECRET=your-jwt-secret-key          # NEVER commit this!
API_KEY=your-secure-api-key             # Internal service auth
DATABASE_URL=postgresql://...           # Database connection
REDIS_URL=redis://redis:6379           # Cache connection
```

## 🔒 Security Responsibilities
- **User Authentication**: Secure JWT token generation and validation
- **Password Security**: bcrypt hashing with configurable rounds
- **API Key Validation**: Constant-time comparison protection
- **Input Validation**: Pydantic model validation for all requests
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries

## 📈 Monitoring Metrics
```python
# Key metrics to track:
platform_auth_attempts_total{result}           # Login attempts
platform_jwt_tokens_active                     # Active sessions
platform_analytics_events_total{type}          # Event tracking
platform_database_query_duration_seconds       # DB performance
platform_redis_cache_hit_rate                  # Cache efficiency
```

## 🎯 Consolidation Benefits

### Before vs After
- **Before**: 2 separate services (Auth + Analytics)
- **After**: 1 unified service

### Resource Efficiency
- 50% reduction in container overhead
- Shared database connections and Redis client
- Unified configuration management
- Single health check endpoint

### Performance Improvements
- Eliminates inter-service HTTP calls
- Shared in-memory caching
- Reduced network latency
- Optimized database queries

## 🔄 Service Communication
```python
# Authentication flow:
Client → API Gateway → Platform Services → PostgreSQL
                            ↓
                      JWT Token Response

# Analytics flow:
Services → Platform Services → PostgreSQL (events/metrics)
                    ↓
              Redis (caching)
```

Remember: This service is the **identity and analytics foundation** for the entire PyAirtable ecosystem. Every user interaction and system metric flows through here!