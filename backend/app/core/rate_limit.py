import time
from fastapi import HTTPException, Request, status
import redis

from .config import get_settings


class RateLimiter:
    def __init__(self) -> None:
        settings = get_settings()
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self.limit = settings.rate_limit_per_minute

    def __call__(self, request: Request) -> None:
        identifier = request.client.host if request.client else "anonymous"
        key = f"rate:{identifier}:{int(time.time() // 60)}"
        current = self.client.incr(key)
        if current == 1:
            self.client.expire(key, 60)
        if current > self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")


def get_rate_limiter() -> RateLimiter:
    return RateLimiter()
