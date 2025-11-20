import dramatiq
from dramatiq.brokers.redis import RedisBroker

from src.core.config import redis_config

redis_broker = RedisBroker(url=redis_config.redis_url)
dramatiq.set_broker(redis_broker)
