import time
from typing import Any, Dict, Optional


class TTLCache:
    """Simple in-memory TTL cache for lightweight scraping results.

    Not thread-safe; acceptable for single-process uvicorn dev usage.
    Keys are strings (e.g. URLs). Values are arbitrary python objects.
    """

    def __init__(self, default_ttl: int = 300, max_size: int = 256):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._store: Dict[str, Any] = {}
        self._expiries: Dict[str, float] = {}

    def _evict_if_needed(self):
        if len(self._store) <= self.max_size:
            return
        # Evict oldest expiry first
        now = time.time()
        expired = [k for k, exp in self._expiries.items() if exp < now]
        for k in expired:
            self._store.pop(k, None)
            self._expiries.pop(k, None)
        if len(self._store) > self.max_size:
            # Hard eviction: remove items with farthest expiry
            sorted_keys = sorted(self._expiries.items(), key=lambda kv: kv[1])
            for k, _ in sorted_keys[: len(self._store) - self.max_size]:
                self._store.pop(k, None)
                self._expiries.pop(k, None)

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        self._store[key] = value
        self._expiries[key] = expiry
        self._evict_if_needed()

    def get(self, key: str) -> Optional[Any]:
        exp = self._expiries.get(key)
        if exp is None:
            return None
        if exp < time.time():
            # Expired
            self._store.pop(key, None)
            self._expiries.pop(key, None)
            return None
        return self._store.get(key)

    def clear(self):
        self._store.clear()
        self._expiries.clear()


# Global instance used by scraping logic
scrape_cache = TTLCache(default_ttl=300, max_size=128)

__all__ = ["scrape_cache", "TTLCache"]
