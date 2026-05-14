"""Reference solution for task_005."""
import time
from collections import OrderedDict


class LRUCacheWithTTL:
    def __init__(self, capacity: int, default_ttl: float, clock=None):
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        if default_ttl <= 0:
            raise ValueError("default_ttl must be > 0")
        self.capacity = capacity
        self.default_ttl = default_ttl
        self.clock = clock if clock is not None else time.monotonic
        self._data: OrderedDict = OrderedDict()  # key -> (value, expires_at)

    def _is_expired(self, expires_at: float) -> bool:
        return self.clock() >= expires_at

    def get(self, key):
        if key not in self._data:
            return None
        value, expires_at = self._data[key]
        if self._is_expired(expires_at):
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key, value, ttl: float | None = None):
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be > 0")
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = self.clock() + effective_ttl
        if key in self._data:
            self._data[key] = (value, expires_at)
            self._data.move_to_end(key)
            return
        self._data[key] = (value, expires_at)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)  # evict LRU

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key) -> bool:
        if key not in self._data:
            return False
        _, expires_at = self._data[key]
        if self._is_expired(expires_at):
            del self._data[key]
            return False
        return True
