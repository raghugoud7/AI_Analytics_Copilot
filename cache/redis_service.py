import json
import os

import redis


class RedisService:
    def __init__(self):
        self.client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
        )

    def get(self, key: str):
        value = self.client.get(key)
        return json.loads(value) if value else None

    def set(self, key: str, value: dict, ttl: int = 3600):
        self.client.setex(key, ttl, json.dumps(value))

    def delete(self, key: str):
        self.client.delete(key)