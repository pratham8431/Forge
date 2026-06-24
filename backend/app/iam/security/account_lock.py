from redis.asyncio import Redis
from app.core.config import settings


def _fail_key(email: str) -> str:
    return f"account:fails:{email}"


def _lock_key(email: str) -> str:
    return f"account:lock:{email}"


async def is_account_locked(redis: Redis, email: str) -> bool:
    return await redis.exists(_lock_key(email)) == 1


async def record_failed_attempt(redis: Redis, email: str) -> int:
    """Increment fail counter. Lock account if threshold reached. Returns current count."""
    fail_key = _fail_key(email)
    count = await redis.incr(fail_key)
    await redis.expire(fail_key, settings.ACCOUNT_LOCK_DURATION)

    if count >= settings.ACCOUNT_LOCK_ATTEMPTS:
        await redis.setex(_lock_key(email), settings.ACCOUNT_LOCK_DURATION, "locked")

    return count


async def clear_failed_attempts(redis: Redis, email: str):
    """Clear on successful login."""
    await redis.delete(_fail_key(email), _lock_key(email))
