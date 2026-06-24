import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, patch

from app.main import app
from app.core.database import Base, get_db
from app.core.redis import get_redis

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
def mock_redis():
    store = {}
    redis = AsyncMock()

    async def setex(key, ttl, val):
        store[key] = val

    async def get(key):
        return store.get(key)

    async def delete(*keys):
        for k in keys:
            store.pop(k, None)

    async def exists(key):
        return 1 if key in store else 0

    async def incr(key):
        store[key] = int(store.get(key, 0)) + 1
        return store[key]

    async def expire(key, ttl):
        pass

    async def zremrangebyscore(key, mn, mx):
        return 0

    async def zadd(key, mapping):
        pass

    async def zcard(key):
        return 1

    redis.setex = setex
    redis.get = get
    redis.delete = delete
    redis.exists = exists
    redis.incr = incr
    redis.expire = expire
    redis.pipeline = AsyncMock(return_value=AsyncMock(
        zremrangebyscore=AsyncMock(return_value=None),
        zadd=AsyncMock(return_value=None),
        zcard=AsyncMock(return_value=1),
        expire=AsyncMock(return_value=None),
        execute=AsyncMock(return_value=[0, None, 1, None]),
    ))
    return redis


@pytest_asyncio.fixture
async def client(db_session, mock_redis):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
