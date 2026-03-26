from functools import wraps
from fastapi import Request, HTTPException, status

from app.core.redis import rate_limiter


def rate_limit(limit: int, window: int):
    """
    Decorator to apply rate limiting to FastAPI endpoints.
    
    Args:
        limit: Maximum number of requests allowed
        window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from kwargs or args
            request: Request = kwargs.get('request')
            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            # Get client identifier (user_id if authenticated, else IP)
            client_id = "anonymous"
            
            # Try to get current_user from kwargs
            current_user = kwargs.get('current_user')
            if current_user:
                client_id = str(current_user.id)
            elif request:
                # Use IP address as fallback
                client_id = request.client.host if request.client else "unknown"
            
            # Create rate limit key
            key = f"rate_limit:{func.__name__}:{client_id}"
            
            # Check rate limit
            allowed, current, remaining = await rate_limiter.is_allowed(
                key, limit, window
            )
            
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {window} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Window": str(window),
                    },
                )
            
            # Add rate limit headers to response
            response = await func(*args, **kwargs)
            
            # If response is a dict, wrap with headers info
            # Note: In real implementation, you'd modify the actual Response object
            return response
        return wrapper
    return decorator