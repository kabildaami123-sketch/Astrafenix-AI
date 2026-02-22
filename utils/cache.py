import time
from typing import Dict, Any, Optional
from collections import OrderedDict

class SimpleCache:
    """
    Simple in-memory cache with TTL
    """
    
    def __init__(self, maxsize: int = 100):
        self.cache = OrderedDict()
        self.maxsize = maxsize
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > time.time():
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL"""
        # Evict oldest if at max size
        if len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)
        
        expiry = time.time() + ttl
        self.cache[key] = (value, expiry)
    
    def clear(self):
        """Clear cache"""
        self.cache.clear()

cache = SimpleCache(maxsize=100)