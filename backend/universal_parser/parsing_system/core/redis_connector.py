import redis


REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0


class RedisConnector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisConnector, cls).__new__(cls)
            cls._instance.client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True,
            )
        return cls._instance

    def get_client(self):
        """Return the Redis client"""
        return self.client


def get_redis_client():
    return RedisConnector().get_client()
