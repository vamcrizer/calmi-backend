"""
In-memory Cache Service cho API responses.

Giảm số lần truy vấn DB cho các endpoint đọc thường xuyên.
Cache tự động hết hạn theo TTL (Time To Live).

Sử dụng:
    from app.core.cache import cache

    # Cache data
    cache.set("moods:user:123:stats", data, ttl=300)  # 5 phút
    
    # Get cached data
    cached = cache.get("moods:user:123:stats")
    
    # Delete cache khi data thay đổi
    cache.delete("moods:user:123:stats")
    cache.delete_pattern("moods:user:123:*")  # Xóa tất cả cache của user
    
    # Decorator cho async functions
    @cached(ttl=300, key_func=lambda user_id: f"moods:stats:{user_id}")
    async def get_mood_stats(user_id: int):
        ...
"""
import time
import re
import functools
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger("app.cache")


class InMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expire_at)
        self.default_ttl = default_ttl  # 5 phút default
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Lấy giá trị từ cache. Trả về None nếu không tồn tại hoặc hết hạn."""
        if key not in self._store:
            self.misses += 1
            return None

        value, expire_at = self._store[key]
        if time.time() > expire_at:
            del self._store[key]
            self.misses += 1
            return None

        self.hits += 1
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Lưu giá trị vào cache với TTL (giây)."""
        # Evict nếu quá size
        if len(self._store) >= self.max_size:
            self._evict_expired()
            if len(self._store) >= self.max_size:
                # Xóa 20% entries cũ nhất
                to_remove = sorted(
                    self._store.items(),
                    key=lambda x: x[1][1]
                )[:self.max_size // 5]
                for k, _ in to_remove:
                    del self._store[k]

        expire_at = time.time() + (ttl or self.default_ttl)
        self._store[key] = (value, expire_at)

    def delete(self, key: str) -> bool:
        """Xóa 1 key khỏi cache."""
        if key in self._store:
            del self._store[key]
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        """Xóa tất cả keys matching pattern (hỗ trợ * wildcard)."""
        regex = re.compile("^" + pattern.replace("*", ".*") + "$")
        keys_to_delete = [k for k in self._store if regex.match(k)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def clear(self) -> None:
        """Xóa toàn bộ cache."""
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def _evict_expired(self) -> int:
        """Xóa tất cả entries đã hết hạn."""
        now = time.time()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(expired)

    def stats(self) -> dict:
        """Thống kê cache."""
        self._evict_expired()
        total = self.hits + self.misses
        return {
            "size": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{(self.hits / total * 100):.1f}%" if total > 0 else "0%",
            "max_size": self.max_size,
        }


# Singleton instance
cache = InMemoryCache(default_ttl=300, max_size=1000)


def cached(ttl: int = 300, key_func: Callable = None):
    """
    Decorator để cache kết quả của async function.
    
    Sử dụng:
        @cached(ttl=300, key_func=lambda user_id, days=7: f"moods:stats:{user_id}:{days}")
        async def get_mood_stats(user_id: int, days: int = 7):
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}.{func.__name__}:{args}:{kwargs}"

            # Check cache
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f"CACHE HIT: {cache_key}")
                return result

            # Call function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                cache.set(cache_key, result, ttl=ttl)
                logger.debug(f"CACHE SET: {cache_key} (ttl={ttl}s)")

            return result

        # Expose cache invalidation
        wrapper.invalidate = lambda *args, **kwargs: cache.delete(
            key_func(*args, **kwargs) if key_func else f"{func.__module__}.{func.__name__}:{args}:{kwargs}"
        )
        return wrapper
    return decorator
