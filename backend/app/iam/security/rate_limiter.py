import time
from redis.asyncio import Redis
from app.core.config import settings


async def check_login_rate_limit(redis: Redis, ip: str) -> bool:
    """
    Redis sliding window rate limiter for login attempts.
    Returns True if request is allowed, False if rate limit exceeded.
    """
    key = f"rate_limit:login:{ip}"
    now = time.time()
    window_start = now - settings.RATE_LIMIT_LOGIN_WINDOW

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, settings.RATE_LIMIT_LOGIN_WINDOW)
    results = await pipe.execute()

    request_count = results[2]
    return request_count <= settings.RATE_LIMIT_LOGIN_MAX
