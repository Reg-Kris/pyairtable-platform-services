"""
Analytics data collector and processor.
"""
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import aiosqlite
from models import Metric, UserStats, SystemMetrics, DailyReport, MetricRecord
from config import ANALYTICS_DB_PATH
from sqlalchemy.orm import Session

class AnalyticsCollector:
    """Analytics data collector for metrics processing."""
    
    def __init__(self, db_path: str = ANALYTICS_DB_PATH):
        self.db_path = db_path
    
    async def init_db(self):
        """Initialize analytics database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    value REAL NOT NULL,
                    user_id TEXT NOT NULL,
                    metadata TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type ON metrics(type)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_user ON metrics(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp)")
            await db.commit()
    
    async def record_metric(self, metric: Metric):
        """Record a single metric."""
        async with aiosqlite.connect(self.db_path) as db:
            metadata_json = json.dumps(metric.metadata) if metric.metadata else None
            await db.execute(
                "INSERT INTO metrics (type, value, user_id, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                (metric.type.value, metric.value, metric.user_id, metadata_json, metric.timestamp)
            )
            await db.commit()
    
    async def record_metric_sync(self, db_session: Session, metric: Metric):
        """Record metric using SQLAlchemy session (for unified DB)."""
        metadata_json = json.dumps(metric.metadata) if metric.metadata else None
        db_metric = MetricRecord(
            type=metric.type.value,
            value=metric.value,
            user_id=metric.user_id,
            metadata=metadata_json,
            timestamp=metric.timestamp
        )
        db_session.add(db_metric)
        db_session.commit()
    
    async def get_user_stats(self, user_id: str, days: int = 7) -> UserStats:
        """Get user statistics for specified period."""
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get aggregated stats
            cursor = await db.execute("""
                SELECT 
                    type,
                    COUNT(*) as count,
                    SUM(value) as total_value,
                    AVG(value) as avg_value
                FROM metrics 
                WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
                GROUP BY type
            """, (user_id, start_date, end_date))
            
            results = await cursor.fetchall()
            
            # Initialize stats
            stats = {
                "api_call": {"count": 0, "total": 0.0},
                "tool_execution": {"count": 0, "total": 0.0},
                "cost": {"count": 0, "total": 0.0},
                "session": {"count": 0, "total": 0.0}
            }
            
            # Process results
            for row in results:
                metric_type, count, total_value, avg_value = row
                if metric_type in stats:
                    stats[metric_type] = {"count": count, "total": total_value or 0.0}
            
            # Calculate session duration if sessions exist
            avg_session_duration = None
            if stats["session"]["count"] > 0:
                avg_session_duration = stats["session"]["total"] / stats["session"]["count"]
            
            return UserStats(
                user_id=user_id,
                days=days,
                api_calls=stats["api_call"]["count"],
                tool_executions=stats["tool_execution"]["count"],
                total_cost=stats["cost"]["total"],
                sessions=stats["session"]["count"],
                avg_session_duration=avg_session_duration,
                period_start=start_date,
                period_end=end_date
            )
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get system-wide metrics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total metrics count
            cursor = await db.execute("SELECT COUNT(*) FROM metrics")
            total_metrics = (await cursor.fetchone())[0]
            
            # Active users (users with metrics in last 24 hours)
            yesterday = datetime.utcnow() - timedelta(days=1)
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT user_id) FROM metrics WHERE timestamp >= ?",
                (yesterday,)
            )
            active_users = (await cursor.fetchone())[0]
            
            # Cost per user (total cost / active users)
            cursor = await db.execute(
                "SELECT AVG(total_cost), AVG(api_calls) FROM ("
                "SELECT user_id, SUM(CASE WHEN type='cost' THEN value ELSE 0 END) as total_cost, "
                "COUNT(CASE WHEN type='api_call' THEN 1 END) as api_calls "
                "FROM metrics WHERE timestamp >= ? GROUP BY user_id)",
                (yesterday,)
            )
            result = await cursor.fetchone()
            cost_per_user = result[0] if result[0] else 0.0
            avg_api_calls = result[1] if result[1] else 0.0
            
            # Peak usage hour
            cursor = await db.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM metrics 
                WHERE timestamp >= ?
                GROUP BY hour 
                ORDER BY count DESC 
                LIMIT 1
            """, (yesterday,))
            peak_result = await cursor.fetchone()
            peak_usage_hour = int(peak_result[0]) if peak_result else None
            
            return SystemMetrics(
                total_metrics=total_metrics,
                active_users=active_users,
                cost_per_user=cost_per_user,
                avg_api_calls_per_user=avg_api_calls,
                peak_usage_hour=peak_usage_hour
            )
    
    async def delete_user_metrics(self, user_id: str) -> int:
        """Delete all metrics for a specific user."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM metrics WHERE user_id = ?", (user_id,))
            await db.commit()
            return cursor.rowcount

class ReportGenerator:
    """Generate analytics reports."""
    
    def __init__(self, db_path: str = ANALYTICS_DB_PATH):
        self.db_path = db_path
    
    async def generate_daily_report(self, date: Optional[str] = None) -> DailyReport:
        """Generate daily system report."""
        if date:
            report_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            report_date = datetime.utcnow().date()
        
        start_time = datetime.combine(report_date, datetime.min.time())
        end_time = datetime.combine(report_date, datetime.max.time())
        
        async with aiosqlite.connect(self.db_path) as db:
            # Total users with activity
            cursor = await db.execute(
                "SELECT COUNT(DISTINCT user_id) FROM metrics WHERE timestamp >= ? AND timestamp <= ?",
                (start_time, end_time)
            )
            total_users = (await cursor.fetchone())[0]
            
            # Aggregated stats
            cursor = await db.execute("""
                SELECT 
                    type,
                    COUNT(*) as count,
                    SUM(value) as total_value
                FROM metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY type
            """, (start_time, end_time))
            
            results = await cursor.fetchall()
            stats = {row[0]: {"count": row[1], "total": row[2]} for row in results}
            
            # Top users by activity
            cursor = await db.execute("""
                SELECT user_id, COUNT(*) as activity_count, SUM(value) as total_value
                FROM metrics 
                WHERE timestamp >= ? AND timestamp <= ?
                GROUP BY user_id 
                ORDER BY activity_count DESC 
                LIMIT 10
            """, (start_time, end_time))
            
            top_users = [
                {"user_id": row[0], "activity_count": row[1], "total_value": row[2]}
                for row in await cursor.fetchall()
            ]
            
            return DailyReport(
                date=report_date.strftime("%Y-%m-%d"),
                total_users=total_users,
                total_api_calls=stats.get("api_call", {}).get("count", 0),
                total_tool_executions=stats.get("tool_execution", {}).get("count", 0),
                total_cost=stats.get("cost", {}).get("total", 0.0),
                total_sessions=stats.get("session", {}).get("count", 0),
                top_users=top_users
            )