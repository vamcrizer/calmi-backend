"""
Simple in-memory cache for API responses.
Useful for caching frequently accessed data.

OPTIMIZED: TTL-based cache with automatic expiration.
"""
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Optional


class TTLCache:
    """Simple TTL-based in-memory cache."""
    
    def __init__(self, default_ttl: int = 60):
        """
        Initialize cache.
        
        Args:
            default_ttl: Default TTL in seconds
        """
        self._cache: dict[str, tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if datetime.utcnow() < expires_at:
                    return value
                else:
                    # Expired, remove it
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl or self._default_ttl)
            self._cache[key] = (value, expires_at)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        async with self._lock:
            self._cache.pop(key, None)
    
    async def clear(self) -> None:
        """Clear all cache."""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns number of items removed."""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = [
                key for key, (_, expires_at) in self._cache.items()
                if now >= expires_at
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Global cache instances
session_cache = TTLCache(default_ttl=300)  # 5 min for session data
user_cache = TTLCache(default_ttl=600)  # 10 min for user data
incident_types_cache = TTLCache(default_ttl=3600)  # 1 hour for static data


def cached(cache: TTLCache, key_func: Callable[..., str], ttl: int = None):
    """
    Decorator for caching async function results.
    
    Usage:
        @cached(session_cache, lambda session_id: f"session:{session_id}")
        async def get_session(session_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = key_func(*args, **kwargs)
            
            # Try cache first
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
