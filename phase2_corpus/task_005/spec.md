# Task 005 — LRU cache with TTL

Difficulty: **medium**
Style: hand-authored

## Class to implement

```python
class LRUCacheWithTTL:
    def __init__(self, capacity: int, default_ttl: float, clock=None): ...
    def get(self, key): ...
    def set(self, key, value, ttl: float | None = None): ...
    def __len__(self) -> int: ...
    def __contains__(self, key) -> bool: ...
```

## Specification

A bounded cache that evicts the least recently used (LRU) entries when
capacity is exceeded, and also expires entries based on a per-entry
time-to-live (TTL).

### Constructor
- `capacity`: positive integer, max entries the cache may hold at once.
  Raise `ValueError` if `capacity < 1`.
- `default_ttl`: positive float, default TTL in seconds for entries
  inserted without an explicit TTL. Raise `ValueError` if `default_ttl <= 0`.
- `clock`: optional zero-argument callable returning the current time as
  a float. Defaults to `time.monotonic`. Used to make TTL testable.

### get(key)
- Returns the value if the key is present AND not expired.
- Returns `None` if the key is missing or expired.
- A successful `get` counts as a use — it moves the key to most-recently-used.
- An expired entry is removed from the cache on get.

### set(key, value, ttl=None)
- Stores `value` under `key`.
- If `ttl` is provided, that's the per-entry TTL (in seconds).
  If `ttl is None`, use `default_ttl`.
- `ttl` must be positive if provided; raise `ValueError` otherwise.
- If the key already exists, update both value and expiry; this counts as a use.
- Setting a new key that puts cache size over capacity must evict
  the least recently used entry first.
- The newly set key is the most recently used.

### __len__()
- Returns the number of entries currently in the cache, **after**
  removing any expired entries lazily encountered.
- It is acceptable for `__len__` to NOT proactively scan for expired
  entries (lazy expiry is fine).

### __contains__(key)
- Returns True if the key is present AND not expired.
- A `__contains__` check does NOT count as a use (does not touch LRU order).
- May remove an expired entry it encounters.

### Time semantics
- An entry inserted at time `t` with ttl `r` is valid for `now < t + r`.
  At exactly `now == t + r` and beyond, the entry is expired.
- The clock returns float seconds and is monotonic; it never goes backward.

## Out of scope

- Thread safety (assume single-threaded use)
- Persistence
- Cache statistics (hit rate, etc.)
- Async/await
