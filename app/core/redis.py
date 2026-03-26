import json
from typing import Optional, Any
from functools import wraps
import hashlib

import redis.asyncio as redis
from app.core.config import settings


class RedisClient:
    """Redis client wrapper with connection pooling and fallback support."""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
        self._available = False
    
    async def connect(self):
        """Initialize Redis connection."""
        try:
            self._client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            self._available = True
            print("✅ Redis connected successfully")
        except Exception as e:
            print(f"⚠️ Redis connection failed: {e}")
            self._available = False
            self._client = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._available = False
    
    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available and self._client is not None
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.is_available:
            return None
        try:
            return await self._client.get(key)
        except Exception:
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
    ) -> bool:
        """Set value with optional expiration (seconds)."""
        if not self.is_available:
            return False
        try:
            await self._client.set(key, value, ex=expire)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key."""
        if not self.is_available:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception:
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.is_available:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception:
            return False
    
    async def incr(self, key: str) -> Optional[int]:
        """Increment value."""
        if not self.is_available:
            return None
        try:
            return await self._client.incr(key)
        except Exception:
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        if not self.is_available:
            return False
        try:
            return await self._client.expire(key, seconds)
        except Exception:
            return False
    
    async def setnx(self, key: str, value: str, expire: Optional[int] = None) -> bool:
        """Set key only if it doesn't exist (for distributed locks)."""
        if not self.is_available:
            return False
        try:
            result = await self._client.setnx(key, value)
            if result and expire:
                await self._client.expire(key, expire)
            return result
        except Exception:
            return False
    
    async def acquire_lock(
        self,
        lock_key: str,
        lock_value: str,
        expire_seconds: int = 30,
    ) -> bool:
        """Acquire distributed lock."""
        return await self.setnx(lock_key, lock_value, expire_seconds)
    
    async def release_lock(self, lock_key: str, lock_value: str) -> bool:
        """Release distributed lock (only if we own it)."""
        if not self.is_available:
            return False
        try:
            # Use Lua script for atomic check-and-delete
            lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
            """
            result = await self._client.eval(lua_script, 1, lock_key, lock_value)
            return result == 1
        except Exception:
            return False


# Global Redis client instance
redis_client = RedisClient()


# ============== CACHE DECORATOR ==============

def cached(expire: int = 300, key_prefix: str = "cache"):
    """
    Decorator to cache function results in Redis.
    
    Args:
        expire: Cache expiration in seconds (default 5 minutes)
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key = f"{key_prefix}:{func.__name__}"
            
            # Add args to key (skip self/db session args)
            for arg in args[1:] if args else []:  # Skip self
                if isinstance(arg, (str, int, float)):
                    cache_key += f":{arg}"
            
            # Add kwargs to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    cache_key += f":{k}={v}"
            
            # Hash long keys
            if len(cache_key) > 200:
                cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(cache_key.encode()).hexdigest()}"
            
            # Try to get from cache
            cached_value = await redis_client.get(cache_key)
            if cached_value:
                try:
                    return json.loads(cached_value)
                except json.JSONDecodeError:
                    pass
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            try:
                await redis_client.set(cache_key, json.dumps(result), expire=expire)
            except (TypeError, ValueError):
                # Can't serialize, skip caching
                pass
            
            return result
        return wrapper
    return decorator


# ============== RATE LIMITING ==============

class RateLimiter:
    """Rate limiter using Redis."""
    
    def __init__(self):
        self.redis = redis_client
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Rate limit key (e.g., user_id or IP)
            limit: Max requests allowed
            window: Time window in seconds
            
        Returns:
            (allowed, current_count, remaining)
        """
        if not self.redis.is_available:
            # Allow if Redis is down (fail open for availability)
            return True, 0, limit
        
        try:
            current = await self.redis.incr(key)
            
            if current == 1:
                # First request, set expiry
                await self.redis.expire(key, window)
            
            remaining = max(0, limit - (current or 0))
            allowed = (current or 0) <= limit
            
            return allowed, current or 0, remaining
        except Exception:
            # Fail open
            return True, 0, limit


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============== TOKEN BLACKLIST ==============

class TokenBlacklist:
    """JWT token blacklist using Redis."""
    
    def __init__(self):
        self.redis = redis_client
    
    async def blacklist_token(self, jti: str, expire_seconds: int) -> bool:
        """Add token JTI to blacklist."""
        key = f"blacklist:{jti}"
        return await self.redis.set(key, "1", expire=expire_seconds)
    
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if token JTI is blacklisted."""
        key = f"blacklist:{jti}"
        return await self.redis.exists(key)


# Global token blacklist instance
token_blacklist = TokenBlacklist()


# ============== DISTRIBUTED LOCKS ==============

class DistributedLock:
    """Distributed locking using Redis."""
    
    def __init__(self):
        self.redis = redis_client
    
    async def acquire(
        self,
        lock_name: str,
        lock_value: str,
        expire_seconds: int = 30,
    ) -> bool:
        """Acquire a distributed lock."""
        return await self.redis.acquire_lock(lock_name, lock_value, expire_seconds)
    
    async def release(self, lock_name: str, lock_value: str) -> bool:
        """Release a distributed lock."""
        return await self.redis.release_lock(lock_name, lock_value)


# Global distributed lock instance
distributed_lock = DistributedLock()