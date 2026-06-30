from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis_client
from app.db.session import get_db

# ── Database ──────────────────────────────────────────────────
DBSession = Annotated[AsyncSession, Depends(get_db)]


# ── Redis ─────────────────────────────────────────────────────
async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_redis_client()


RedisClient = Annotated[aioredis.Redis, Depends(get_redis)]
