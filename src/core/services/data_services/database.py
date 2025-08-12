"""
Database service for FS Reconciliation Agents.

This module provides database connection management, session handling,
and database utilities for the reconciliation system.
"""

import os
import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Database configuration
# Convert standard PostgreSQL URL to async URL if needed
raw_database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://reconciliation_user:reconciliation_password@database:5432/reconciliation_db"
)

# Ensure we're using asyncpg for async operations
if raw_database_url.startswith("postgresql://"):
    DATABASE_URL = raw_database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_database_url

# Engine configuration
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=3600
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def get_db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to inject database session."""
    async with get_db_session() as session:
        yield session


async def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_database_info() -> dict:
    """Get database information and statistics."""
    try:
        async with get_db_session() as session:
            # Get database version
            version_result = await session.execute(text("SELECT version()"))
            version = version_result.scalar()
            
            # Get database size
            size_result = await session.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            ))
            size = size_result.scalar()
            
            # Get table counts
            tables_result = await session.execute(text("""
                SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                FROM pg_stat_user_tables
                ORDER BY schemaname, tablename
            """))
            tables = [dict(row._mapping) for row in tables_result]
            
            return {
                "version": version,
                "size": size,
                "tables": tables,
                "status": "connected"
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


async def execute_migration() -> bool:
    """Execute database migrations."""
    try:
        # This would typically use Alembic
        # For now, we'll just check if tables exist
        async with get_db_session() as session:
            # Check if main tables exist
            tables_result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('transactions', 'reconciliation_exceptions', 'audit_trail')
            """))
            existing_tables = [row[0] for row in tables_result]
            
            required_tables = ['transactions', 'reconciliation_exceptions', 'audit_trail']
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
            
            return True
    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        return False


async def cleanup_old_data() -> dict:
    """Clean up old data based on retention policies."""
    try:
        async with get_db_session() as session:
            # Get retention configuration
            audit_retention_days = int(os.getenv("AUDIT_TRAIL_RETENTION_DAYS", "2555"))
            transaction_retention_days = int(os.getenv("TRANSACTIONS_RETENTION_DAYS", "1825"))
            exception_retention_days = int(os.getenv("EXCEPTIONS_RETENTION_DAYS", "1825"))
            
            cleanup_stats = {
                "audit_trail": 0,
                "transactions": 0,
                "exceptions": 0,
                "errors": []
            }
            
            # Clean up old audit trail entries
            try:
                audit_result = await session.execute(text(f"""
                    DELETE FROM audit_trail 
                    WHERE created_at < NOW() - INTERVAL '{audit_retention_days} days'
                """))
                cleanup_stats["audit_trail"] = audit_result.rowcount
            except Exception as e:
                cleanup_stats["errors"].append(f"Audit trail cleanup failed: {e}")
            
            # Clean up old transactions
            try:
                transaction_result = await session.execute(text(f"""
                    DELETE FROM transactions 
                    WHERE created_at < NOW() - INTERVAL '{transaction_retention_days} days'
                """))
                cleanup_stats["transactions"] = transaction_result.rowcount
            except Exception as e:
                cleanup_stats["errors"].append(f"Transaction cleanup failed: {e}")
            
            # Clean up old exceptions
            try:
                exception_result = await session.execute(text(f"""
                    DELETE FROM reconciliation_exceptions 
                    WHERE created_at < NOW() - INTERVAL '{exception_retention_days} days'
                """))
                cleanup_stats["exceptions"] = exception_result.rowcount
            except Exception as e:
                cleanup_stats["errors"].append(f"Exception cleanup failed: {e}")
            
            await session.commit()
            return cleanup_stats
            
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")
        return {
            "audit_trail": 0,
            "transactions": 0,
            "exceptions": 0,
            "errors": [str(e)]
        }


async def get_database_metrics() -> dict:
    """Get database performance metrics."""
    try:
        async with get_db_session() as session:
            # Get connection count
            connections_result = await session.execute(text("""
                SELECT count(*) as active_connections 
                FROM pg_stat_activity 
                WHERE state = 'active'
            """))
            active_connections = connections_result.scalar()
            
            # Get slow queries
            slow_queries_result = await session.execute(text("""
                SELECT query, mean_time, calls
                FROM pg_stat_statements 
                WHERE mean_time > 1000
                ORDER BY mean_time DESC 
                LIMIT 10
            """))
            slow_queries = [dict(row._mapping) for row in slow_queries_result]
            
            # Get table sizes
            table_sizes_result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """))
            table_sizes = [dict(row._mapping) for row in table_sizes_result]
            
            return {
                "active_connections": active_connections,
                "slow_queries": slow_queries,
                "table_sizes": table_sizes,
                "timestamp": "2024-01-01T00:00:00Z"  # TODO: Use actual timestamp
            }
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        return {
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }


# Database health check
async def health_check_database() -> dict:
    """Health check for database."""
    try:
        # Test connection
        connection_ok = await check_database_connection()
        
        if not connection_ok:
            return {
                "status": "unhealthy",
                "error": "Database connection failed"
            }
        
        # Get basic metrics
        metrics = await get_database_metrics()
        
        return {
            "status": "healthy",
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        } 