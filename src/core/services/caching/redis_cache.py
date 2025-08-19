"""
Redis Caching Service for FS Reconciliation Agents.

This module provides a comprehensive caching layer using Redis for:
- API response caching
- Database query caching
- Session management
- File processing cache
- Real-time data caching
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import asyncio

import redis.asyncio as redis
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheConfig(BaseModel):
    """Configuration for cache settings."""
    redis_url: str = "redis://localhost:6379"
    default_ttl: int = 300  # 5 minutes
    max_connections: int = 20
    retry_attempts: int = 3
    retry_delay: float = 0.1
    
    # Cache layer TTLs
    api_response_ttl: int = 300      # 5 minutes
    query_cache_ttl: int = 600       # 10 minutes
    session_ttl: int = 1800          # 30 minutes
    file_cache_ttl: int = 3600       # 1 hour
    analytics_ttl: int = 7200        # 2 hours


class RedisCacheService:
    """Redis caching service with multiple caching strategies."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis_pool = None
        self._connection_lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize Redis connection pool."""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.max_connections,
                decode_responses=True
            )
            logger.info("Redis cache service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {e}")
            raise
    
    async def get_connection(self) -> redis.Redis:
        """Get Redis connection from pool."""
        if not self.redis_pool:
            await self.initialize()
        return redis.Redis(connection_pool=self.redis_pool)
    
    async def close(self):
        """Close Redis connections."""
        if self.redis_pool:
            await self.redis_pool.disconnect()
            logger.info("Redis cache service closed")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments."""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        # Create hash for long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 250:  # Redis key length limit
            return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
        
        return key_string
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cache value with optional TTL."""
        try:
            redis_client = await self.get_connection()
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or self.config.default_ttl
            
            result = await redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return result
        except Exception as e:
            logger.error(f"Cache SET failed for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cache value."""
        try:
            redis_client = await self.get_connection()
            value = await redis_client.get(key)
            
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache GET failed for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete cache key."""
        try:
            redis_client = await self.get_connection()
            result = await redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache DELETE failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            redis_client = await self.get_connection()
            return bool(await redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache EXISTS failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration for existing key."""
        try:
            redis_client = await self.get_connection()
            return bool(await redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Cache EXPIRE failed for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            redis_client = await self.get_connection()
            keys = await redis_client.keys(pattern)
            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache CLEAR_PATTERN failed for pattern {pattern}: {e}")
            return 0


class APICacheService:
    """API response caching service."""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.prefix = "api:response"
    
    def cache_response(self, ttl: Optional[int] = None):
        """Decorator to cache API responses."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                cache_key = self.cache._generate_key(
                    self.prefix, 
                    func.__name__, 
                    *args, 
                    **kwargs
                )
                
                # Try to get from cache
                cached_result = await self.cache.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function and cache result
                result = await func(*args, **kwargs)
                cache_ttl = ttl or self.cache.config.api_response_ttl
                await self.cache.set(cache_key, result, cache_ttl)
                
                return result
            return wrapper
        return decorator
    
    async def invalidate_endpoint(self, endpoint: str, **filters):
        """Invalidate cache for specific endpoint."""
        pattern = f"{self.prefix}:{endpoint}:*"
        return await self.cache.clear_pattern(pattern)


class QueryCacheService:
    """Database query caching service."""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.prefix = "query:cache"
    
    async def cache_query(self, query_hash: str, result: Any, ttl: Optional[int] = None):
        """Cache database query result."""
        cache_key = f"{self.prefix}:{query_hash}"
        cache_ttl = ttl or self.cache.config.query_cache_ttl
        return await self.cache.set(cache_key, result, cache_ttl)
    
    async def get_cached_query(self, query_hash: str) -> Optional[Any]:
        """Get cached query result."""
        cache_key = f"{self.prefix}:{query_hash}"
        return await self.cache.get(cache_key)
    
    async def invalidate_table(self, table_name: str):
        """Invalidate all cached queries for a table."""
        pattern = f"{self.prefix}:*:{table_name}:*"
        return await self.cache.clear_pattern(pattern)
    
    def query_cache(self, ttl: Optional[int] = None):
        """Decorator to cache database queries."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate query hash
                query_hash = hashlib.md5(
                    f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}".encode()
                ).hexdigest()
                
                # Try to get from cache
                cached_result = await self.get_cached_query(query_hash)
                if cached_result is not None:
                    return cached_result
                
                # Execute query and cache result
                result = await func(*args, **kwargs)
                cache_ttl = ttl or self.cache.config.query_cache_ttl
                await self.cache_query(query_hash, result, cache_ttl)
                
                return result
            return wrapper
        return decorator


class SessionCacheService:
    """Session management cache service."""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.prefix = "session"
    
    async def store_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Store user session data."""
        cache_key = f"{self.prefix}:{session_id}"
        return await self.cache.set(cache_key, session_data, self.cache.config.session_ttl)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        cache_key = f"{self.prefix}:{session_id}"
        return await self.cache.get(cache_key)
    
    async def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update existing session data."""
        cache_key = f"{self.prefix}:{session_id}"
        return await self.cache.set(cache_key, session_data, self.cache.config.session_ttl)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete user session."""
        cache_key = f"{self.prefix}:{session_id}"
        return await self.cache.delete(cache_key)
    
    async def extend_session(self, session_id: str) -> bool:
        """Extend session TTL."""
        cache_key = f"{self.prefix}:{session_id}"
        return await self.cache.expire(cache_key, self.cache.config.session_ttl)


class FileCacheService:
    """File processing cache service."""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.prefix = "file:cache"
    
    async def cache_file_metadata(self, file_hash: str, metadata: Dict[str, Any]) -> bool:
        """Cache file processing metadata."""
        cache_key = f"{self.prefix}:metadata:{file_hash}"
        return await self.cache.set(cache_key, metadata, self.cache.config.file_cache_ttl)
    
    async def get_file_metadata(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached file metadata."""
        cache_key = f"{self.prefix}:metadata:{file_hash}"
        return await self.cache.get(cache_key)
    
    async def cache_processing_result(self, file_hash: str, result: Dict[str, Any]) -> bool:
        """Cache file processing result."""
        cache_key = f"{self.prefix}:result:{file_hash}"
        return await self.cache.set(cache_key, result, self.cache.config.file_cache_ttl)
    
    async def get_processing_result(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached processing result."""
        cache_key = f"{self.prefix}:result:{file_hash}"
        return await self.cache.get(cache_key)
    
    async def invalidate_file_cache(self, file_hash: str) -> int:
        """Invalidate all cache entries for a file."""
        pattern = f"{self.prefix}:*:{file_hash}"
        return await self.cache.clear_pattern(pattern)


class AnalyticsCacheService:
    """Analytics and reporting cache service."""
    
    def __init__(self, cache_service: RedisCacheService):
        self.cache = cache_service
        self.prefix = "analytics"
    
    async def cache_dashboard_data(self, dashboard_id: str, data: Dict[str, Any]) -> bool:
        """Cache dashboard data."""
        cache_key = f"{self.prefix}:dashboard:{dashboard_id}"
        return await self.cache.set(cache_key, data, self.cache.config.analytics_ttl)
    
    async def get_dashboard_data(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get cached dashboard data."""
        cache_key = f"{self.prefix}:dashboard:{dashboard_id}"
        return await self.cache.get(cache_key)
    
    async def cache_report(self, report_type: str, parameters: Dict[str, Any], data: Any) -> bool:
        """Cache report data."""
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        cache_key = f"{self.prefix}:report:{report_type}:{param_hash}"
        return await self.cache.set(cache_key, data, self.cache.config.analytics_ttl)
    
    async def get_cached_report(self, report_type: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """Get cached report data."""
        param_hash = hashlib.md5(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        cache_key = f"{self.prefix}:report:{report_type}:{param_hash}"
        return await self.cache.get(cache_key)
    
    async def invalidate_analytics(self, pattern: str = "*") -> int:
        """Invalidate analytics cache."""
        full_pattern = f"{self.prefix}:{pattern}"
        return await self.cache.clear_pattern(full_pattern)


# Global cache service instance
_cache_service: Optional[RedisCacheService] = None
_api_cache: Optional[APICacheService] = None
_query_cache: Optional[QueryCacheService] = None
_session_cache: Optional[SessionCacheService] = None
_file_cache: Optional[FileCacheService] = None
_analytics_cache: Optional[AnalyticsCacheService] = None


async def initialize_cache_service(config: CacheConfig):
    """Initialize global cache service."""
    global _cache_service, _api_cache, _query_cache, _session_cache, _file_cache, _analytics_cache
    
    _cache_service = RedisCacheService(config)
    await _cache_service.initialize()
    
    _api_cache = APICacheService(_cache_service)
    _query_cache = QueryCacheService(_cache_service)
    _session_cache = SessionCacheService(_cache_service)
    _file_cache = FileCacheService(_cache_service)
    _analytics_cache = AnalyticsCacheService(_cache_service)
    
    logger.info("Global cache services initialized")


def get_cache_service() -> RedisCacheService:
    """Get global cache service instance."""
    if not _cache_service:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _cache_service


def get_api_cache() -> APICacheService:
    """Get API cache service instance."""
    if not _api_cache:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _api_cache


def get_query_cache() -> QueryCacheService:
    """Get query cache service instance."""
    if not _query_cache:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _query_cache


def get_session_cache() -> SessionCacheService:
    """Get session cache service instance."""
    if not _session_cache:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _session_cache


def get_file_cache() -> FileCacheService:
    """Get file cache service instance."""
    if not _file_cache:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _file_cache


def get_analytics_cache() -> AnalyticsCacheService:
    """Get analytics cache service instance."""
    if not _analytics_cache:
        raise RuntimeError("Cache service not initialized. Call initialize_cache_service() first.")
    return _analytics_cache
