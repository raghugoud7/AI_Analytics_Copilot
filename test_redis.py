from cache.redis_service import RedisService

redis_client = RedisService()

redis_client.set("test", {"message": "hello"})
print(redis_client.get("test"))