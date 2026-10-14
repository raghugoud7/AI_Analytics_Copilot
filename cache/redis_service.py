import json
import time

import redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError
from redis.backoff import NoBackoff
from redis.retry import Retry

from config.settings import (
    REDIS_DB,
    REDIS_HOST,
    REDIS_PASSWORD,
    REDIS_PORT,
    REDIS_SSL,
)


class RedisService:

    def __init__(self):
        self.disabled_until = 0.0

        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD or None,
            ssl=REDIS_SSL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            retry=Retry(NoBackoff(), 0),
            retry_on_timeout=False,
            health_check_interval=30,
        )

    def _available(self) -> bool:
        return time.time() >= self.disabled_until

    def _disable_temporarily(self, seconds: int = 60) -> None:
        self.disabled_until = time.time() + seconds

    def get(self, key: str) -> dict | None:
        if not self._available():
            return None

        try:
            value = self.client.get(key)
            return json.loads(value) if value else None

        except (ConnectionError, TimeoutError, RedisError, json.JSONDecodeError) as ex:
            print(f"Redis GET skipped: {ex}")
            self._disable_temporarily()
            return None

    def set(self, key: str, value: dict, ttl: int = 3600) -> bool:
        if not self._available():
            return False

        try:
            self.client.setex(key, ttl, json.dumps(value, default=str))
            return True

        except (ConnectionError, TimeoutError, RedisError, TypeError) as ex:
            print(f"Redis SET skipped: {ex}")
            self._disable_temporarily()
            return False

    def delete(self, key: str) -> bool:
        if not self._available():
            return False

        try:
            self.client.delete(key)
            return True

        except (ConnectionError, TimeoutError, RedisError) as ex:
            print(f"Redis DELETE skipped: {ex}")
            self._disable_temporarily()
            return False

    def ping(self) -> bool:
        if not self._available():
            return False

        try:
            return bool(self.client.ping())

        except (ConnectionError, TimeoutError, RedisError) as ex:
            print(f"Redis PING failed: {ex}")
            self._disable_temporarily()
            return False