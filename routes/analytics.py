"""
Analytics routes for Platform Services
Event tracking, metrics collection, and usage analytics
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timedelta

from database import get_db, AnalyticsEvent, AnalyticsMetric, AnalyticsUsage, get_redis
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class EventCreate(BaseModel):
    event_type: str
    event_data: Optional[Dict[str, Any]] = {}
    user_id: Optional[int] = None
    session_id: Optional[str] = None

class MetricCreate(BaseModel):
    metric_name: str
    metric_value: float
    metric_type: str = "counter"  # counter, gauge, histogram
    user_id: Optional[int] = None
    service_name: Optional[str] = None
    endpoint: Optional[str] = None
    labels: Optional[Dict[str, Any]] = {}

class BatchMetricCreate(BaseModel):
    metrics: List[MetricCreate]

class EventResponse(BaseModel):
    id: int
    event_type: str
    event_data: Dict[str, Any]
    user_id: Optional[int]
    session_id: Optional[str]
    timestamp: datetime

class MetricResponse(BaseModel):
    id: int
    metric_name: str
    metric_value: float
    metric_type: str
    user_id: Optional[int]
    service_name: Optional[str]
    endpoint: Optional[str]
    labels: Dict[str, Any]
    timestamp: datetime

class UsageResponse(BaseModel):
    user_id: int
    api_calls_count: int
    tokens_used: int
    cost_usd: float
    date: datetime
    period_type: str

class DashboardMetrics(BaseModel):
    total_events: int
    active_users: int
    total_api_calls: int
    total_cost: float
    top_endpoints: List[Dict[str, Any]]
    recent_events: List[EventResponse]

# Helper functions
def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")

# Analytics endpoints
@router.post("/events", response_model=EventResponse)
async def track_event(
    event: EventCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Track analytics event"""
    try:
        # Create analytics event
        analytics_event = AnalyticsEvent(
            event_type=event.event_type,
            event_data=event.event_data or {},
            user_id=event.user_id,
            session_id=event.session_id,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )
        
        db.add(analytics_event)
        await db.commit()
        await db.refresh(analytics_event)
        
        # Cache recent events in Redis for dashboard
        redis = await get_redis()
        if redis:
            try:
                event_data = {
                    "id": analytics_event.id,
                    "event_type": analytics_event.event_type,
                    "user_id": analytics_event.user_id,
                    "timestamp": analytics_event.timestamp.isoformat()
                }
                await redis.lpush("recent_events", str(event_data))
                await redis.ltrim("recent_events", 0, 99)  # Keep last 100 events
            except Exception as e:
                logger.warning(f"Failed to cache event in Redis: {str(e)}")
        
        logger.info(f"Event tracked: {event.event_type} for user {event.user_id}")
        
        return EventResponse(
            id=analytics_event.id,
            event_type=analytics_event.event_type,
            event_data=analytics_event.event_data,
            user_id=analytics_event.user_id,
            session_id=analytics_event.session_id,
            timestamp=analytics_event.timestamp
        )
        
    except Exception as e:
        logger.error(f"Event tracking error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Event tracking failed")

@router.post("/metrics", response_model=MetricResponse)
async def create_metric(
    metric: MetricCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create analytics metric"""
    try:
        analytics_metric = AnalyticsMetric(
            metric_name=metric.metric_name,
            metric_value=metric.metric_value,
            metric_type=metric.metric_type,
            user_id=metric.user_id,
            service_name=metric.service_name,
            endpoint=metric.endpoint,
            labels=metric.labels or {}
        )
        
        db.add(analytics_metric)
        await db.commit()
        await db.refresh(analytics_metric)
        
        logger.debug(f"Metric created: {metric.metric_name} = {metric.metric_value}")
        
        return MetricResponse(
            id=analytics_metric.id,
            metric_name=analytics_metric.metric_name,
            metric_value=analytics_metric.metric_value,
            metric_type=analytics_metric.metric_type,
            user_id=analytics_metric.user_id,
            service_name=analytics_metric.service_name,
            endpoint=analytics_metric.endpoint,
            labels=analytics_metric.labels,
            timestamp=analytics_metric.timestamp
        )
        
    except Exception as e:
        logger.error(f"Metric creation error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Metric creation failed")

@router.post("/metrics/batch")
async def create_metrics_batch(
    batch: BatchMetricCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create multiple metrics in batch"""
    try:
        metrics = []
        for metric_data in batch.metrics:
            metric = AnalyticsMetric(
                metric_name=metric_data.metric_name,
                metric_value=metric_data.metric_value,
                metric_type=metric_data.metric_type,
                user_id=metric_data.user_id,
                service_name=metric_data.service_name,
                endpoint=metric_data.endpoint,
                labels=metric_data.labels or {}
            )
            metrics.append(metric)
        
        db.add_all(metrics)
        await db.commit()
        
        logger.info(f"Batch created {len(metrics)} metrics")
        
        return {"message": f"Created {len(metrics)} metrics successfully"}
        
    except Exception as e:
        logger.error(f"Batch metric creation error: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Batch metric creation failed")

@router.get("/metrics")
async def get_metrics(
    metric_name: Optional[str] = None,
    service_name: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get analytics metrics with filtering"""
    try:
        query = select(AnalyticsMetric).order_by(desc(AnalyticsMetric.timestamp))
        
        # Apply filters
        if metric_name:
            query = query.where(AnalyticsMetric.metric_name == metric_name)
        if service_name:
            query = query.where(AnalyticsMetric.service_name == service_name)
        if user_id:
            query = query.where(AnalyticsMetric.user_id == user_id)
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        metrics = result.scalars().all()
        
        return {
            "metrics": [
                MetricResponse(
                    id=m.id,
                    metric_name=m.metric_name,
                    metric_value=m.metric_value,
                    metric_type=m.metric_type,
                    user_id=m.user_id,
                    service_name=m.service_name,
                    endpoint=m.endpoint,
                    labels=m.labels,
                    timestamp=m.timestamp
                ) for m in metrics
            ],
            "count": len(metrics)
        }
        
    except Exception as e:
        logger.error(f"Metrics retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="Metrics retrieval failed")

@router.get("/usage/{user_id}", response_model=List[UsageResponse])
async def get_user_usage(
    user_id: int,
    period_type: str = "daily",
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get user usage statistics"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query usage data
        query = select(AnalyticsUsage).where(
            and_(
                AnalyticsUsage.user_id == user_id,
                AnalyticsUsage.period_type == period_type,
                AnalyticsUsage.date >= start_date,
                AnalyticsUsage.date <= end_date
            )
        ).order_by(desc(AnalyticsUsage.date))
        
        result = await db.execute(query)
        usage_records = result.scalars().all()
        
        return [
            UsageResponse(
                user_id=record.user_id,
                api_calls_count=record.api_calls_count,
                tokens_used=record.tokens_used,
                cost_usd=record.cost_usd,
                date=record.date,
                period_type=record.period_type
            ) for record in usage_records
        ]
        
    except Exception as e:
        logger.error(f"User usage retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail="User usage retrieval failed")

@router.get("/costs")
async def get_costs(
    user_id: Optional[int] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get cost breakdown and analysis"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Base query for usage data
        query = select(AnalyticsUsage).where(
            and_(
                AnalyticsUsage.date >= start_date,
                AnalyticsUsage.date <= end_date
            )
        )
        
        if user_id:
            query = query.where(AnalyticsUsage.user_id == user_id)
        
        result = await db.execute(query)
        usage_records = result.scalars().all()
        
        # Calculate totals
        total_cost = sum(record.cost_usd for record in usage_records)
        total_tokens = sum(record.tokens_used for record in usage_records)
        total_api_calls = sum(record.api_calls_count for record in usage_records)
        
        # Group by user for breakdown
        user_costs = {}
        for record in usage_records:
            if record.user_id not in user_costs:
                user_costs[record.user_id] = {
                    "user_id": record.user_id,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "total_api_calls": 0
                }
            user_costs[record.user_id]["total_cost"] += record.cost_usd
            user_costs[record.user_id]["total_tokens"] += record.tokens_used
            user_costs[record.user_id]["total_api_calls"] += record.api_calls_count
        
        return {
            "summary": {
                "total_cost_usd": round(total_cost, 4),
                "total_tokens": total_tokens,
                "total_api_calls": total_api_calls,
                "period_days": days,
                "cost_per_token": round(total_cost / total_tokens, 6) if total_tokens > 0 else 0,
                "cost_per_api_call": round(total_cost / total_api_calls, 4) if total_api_calls > 0 else 0
            },
            "user_breakdown": list(user_costs.values()),
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Cost analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail="Cost analysis failed")

@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard metrics for the last N hours"""
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Count total events
        events_query = select(func.count(AnalyticsEvent.id)).where(
            AnalyticsEvent.timestamp >= start_time
        )
        total_events_result = await db.execute(events_query)
        total_events = total_events_result.scalar() or 0
        
        # Count active users
        active_users_query = select(func.count(func.distinct(AnalyticsEvent.user_id))).where(
            and_(
                AnalyticsEvent.timestamp >= start_time,
                AnalyticsEvent.user_id.isnot(None)
            )
        )
        active_users_result = await db.execute(active_users_query)
        active_users = active_users_result.scalar() or 0
        
        # Get API call metrics
        api_calls_query = select(func.sum(AnalyticsMetric.metric_value)).where(
            and_(
                AnalyticsMetric.metric_name == "api_calls",
                AnalyticsMetric.timestamp >= start_time
            )
        )
        api_calls_result = await db.execute(api_calls_query)
        total_api_calls = int(api_calls_result.scalar() or 0)
        
        # Get cost metrics
        cost_query = select(func.sum(AnalyticsUsage.cost_usd)).where(
            AnalyticsUsage.date >= start_time.date()
        )
        cost_result = await db.execute(cost_query)
        total_cost = float(cost_result.scalar() or 0.0)
        
        # Get top endpoints
        endpoints_query = select(
            AnalyticsMetric.endpoint,
            func.count(AnalyticsMetric.id).label('count')
        ).where(
            and_(
                AnalyticsMetric.timestamp >= start_time,
                AnalyticsMetric.endpoint.isnot(None)
            )
        ).group_by(AnalyticsMetric.endpoint).order_by(desc('count')).limit(5)
        
        endpoints_result = await db.execute(endpoints_query)
        top_endpoints = [
            {"endpoint": row.endpoint, "count": row.count}
            for row in endpoints_result
        ]
        
        # Get recent events
        recent_events_query = select(AnalyticsEvent).where(
            AnalyticsEvent.timestamp >= start_time
        ).order_by(desc(AnalyticsEvent.timestamp)).limit(10)
        
        recent_events_result = await db.execute(recent_events_query)
        recent_events = [
            EventResponse(
                id=event.id,
                event_type=event.event_type,
                event_data=event.event_data,
                user_id=event.user_id,
                session_id=event.session_id,
                timestamp=event.timestamp
            ) for event in recent_events_result.scalars()
        ]
        
        return DashboardMetrics(
            total_events=total_events,
            active_users=active_users,
            total_api_calls=total_api_calls,
            total_cost=total_cost,
            top_endpoints=top_endpoints,
            recent_events=recent_events
        )
        
    except Exception as e:
        logger.error(f"Dashboard metrics error: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard metrics retrieval failed")