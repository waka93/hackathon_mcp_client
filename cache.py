from cachetools import TTLCache

class SingletonTTLCache:
    _instance = None

    def __new__(cls, maxsize=100, ttl=300):
        if cls._instance is None:
            cls._instance = TTLCache(maxsize=maxsize, ttl=ttl)
        return cls._instance

CACHE = SingletonTTLCache(ttl=3600 * 24)