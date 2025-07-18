from typing import Any, Optional
import json
from redis import Redis
from app.core.config import settings

class RedisCache:
    def __init__(self):
        self.redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.default_expire = settings.REDIS_CACHE_EXPIRE_MINUTES * 60

    def _generate_key(self, key_parts: list[Any]) -> str:
        """Generate a consistent cache key from multiple parts"""
        return ":".join(str(part) for part in key_parts)

    async def get(self, key_parts: list[Any]) -> Optional[str]:
        """Get value from cache"""
        key = self._generate_key(key_parts)
        return self.redis_client.get(key)

    async def set(
        self,
        key_parts: list[Any],
        value: Any,
        expire: int | None = None
    ) -> None:
        """Set value in cache"""
        key = self._generate_key(key_parts)
        self.redis_client.set(
            key,
            json.dumps(value),
            ex=expire or self.default_expire
        )

    async def delete(self, key_parts: list[Any]) -> None:
        """Delete value from cache"""
        key = self._generate_key(key_parts)
        self.redis_client.delete(key)

    async def invalidate_pattern(self, pattern: str) -> None:
        """Delete all keys matching pattern"""
        keys = self.redis_client.keys(pattern)
        if keys:
            self.redis_client.delete(*keys)


# Global cache instance
cache = RedisCache()
