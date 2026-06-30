import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_client: aioredis.Redis | None = None


def get_redis_client() -> aioredis.Redis:
    if _client is None:
        raise RuntimeError("Redis has not been initialized — call connect_redis() first.")
    return _client


async def connect_redis(url: str) -> None:
    global _client
    _client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
    await _client.ping()
    logger.info("Redis connected", extra={"url": url.split("@")[-1]})


async def disconnect_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
        logger.info("Redis disconnected")
