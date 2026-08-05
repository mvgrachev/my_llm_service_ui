"""Redis cache client for LLM Service."""
import json
import hashlib
import logging
from typing import Optional, Any
from datetime import timedelta
from config import settings

logger = logging.getLogger('llm_service.cache')


class CacheClient:
    """Redis cache client for storing and retrieving LLM responses."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0, url: str = None):
        """
        Initialize Redis cache client.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            url: Redis URL (overrides host/port/db)
        """
        self.redis_available = False
        self._cache = None
        
        try:
            import redis
            if url:
                self._cache = redis.from_url(url)
            else:
                self._cache = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            # Test connection
            self._cache.ping()
            self.redis_available = True
        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self.redis_available = False
            self._cache = None
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = self._cache.get(key)
            if value:
                logger.info(f"[CACHE Redis] Hit for key: {key[:50]}...")
                return json.loads(value)
            else:
                logger.info(f"[CACHE Redis] Miss for key: {key[:50]}...")
            return None
        except Exception as e:
            logger.error(f"[CACHE Redis] Error getting key {key[:50]}...: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 600) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 600 = 10 minutes)
            
        Returns:
            True if successful
        """
        try:
            self._cache.setex(key, ttl, json.dumps(value))
            logger.debug(f"[CACHE Redis] Set key: {key[:50]}... with TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"[CACHE Redis] Error setting key {key[:50]}...: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key was deleted
        """
        try:
            self._cache.delete(key)
            logger.debug(f"[CACHE Redis] Deleted key: {key[:50]}...")
            return True
        except Exception as e:
            logger.error(f"[CACHE Redis] Error deleting key {key[:50]}...: {str(e)}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        try:
            return self._cache.exists(key) > 0
        except Exception as e:
            logger.error(f"[CACHE Redis] Error checking key existence {key[:50]}...: {str(e)}")
            return False


# Default cache instance — created lazily to avoid connection errors on import
_cache_instance = None


def get_cache():
    """Lazily create and return the default cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheClient(url=settings.redis_url)
    return _cache_instance


class _LazyCache:
    """Proxy that forwards attribute access to the lazily-created cache.
    
    If Redis is unavailable, get() returns None (cache miss),
    set()/delete()/exists() return False — the application continues
    to work without caching.
    """

    def __getattr__(self, name):
        return getattr(get_cache(), name)

    def get(self, key: str):
        """Get from cache. Returns None if Redis is unavailable."""
        client = get_cache()
        if not client.redis_available:
            logger.info(f"[CACHE Redis] Unavailable — cache miss for key: {key[:50]}...")
            return None
        return client.get(key)

    def set(self, key: str, value: Any, ttl: int = 600) -> bool:
        """Set in cache. Returns False if Redis is unavailable."""
        client = get_cache()
        if not client.redis_available:
            logger.debug(f"[CACHE Redis] Unavailable — skipping set for key: {key[:50]}...")
            return False
        return client.set(key, value, ttl)

    def delete(self, key: str) -> bool:
        """Delete from cache. Returns False if Redis is unavailable."""
        client = get_cache()
        if not client.redis_available:
            return False
        return client.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists. Returns False if Redis is unavailable."""
        client = get_cache()
        if not client.redis_available:
            return False
        return client.exists(key)


cache = _LazyCache()
