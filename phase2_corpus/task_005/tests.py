"""Tests for LRUCacheWithTTL."""
import pytest
from solution import LRUCacheWithTTL


class FakeClock:
    """Manually-advanced clock for deterministic TTL tests."""
    def __init__(self, start: float = 0.0):
        self.t = start
    def __call__(self) -> float:
        return self.t
    def advance(self, seconds: float):
        self.t += seconds


# --- construction ---

def test_zero_capacity_rejected():
    with pytest.raises(ValueError):
        LRUCacheWithTTL(capacity=0, default_ttl=10)


def test_zero_ttl_rejected():
    with pytest.raises(ValueError):
        LRUCacheWithTTL(capacity=10, default_ttl=0)


# --- basic get/set ---

def test_set_and_get():
    c = LRUCacheWithTTL(capacity=10, default_ttl=60)
    c.set("a", 1)
    assert c.get("a") == 1


def test_get_missing_returns_none():
    c = LRUCacheWithTTL(capacity=10, default_ttl=60)
    assert c.get("missing") is None


def test_set_overwrites_existing():
    c = LRUCacheWithTTL(capacity=10, default_ttl=60)
    c.set("a", 1)
    c.set("a", 2)
    assert c.get("a") == 2


def test_len_reflects_entries():
    c = LRUCacheWithTTL(capacity=10, default_ttl=60)
    c.set("a", 1)
    c.set("b", 2)
    assert len(c) == 2


def test_contains_checks_presence():
    c = LRUCacheWithTTL(capacity=10, default_ttl=60)
    c.set("a", 1)
    assert "a" in c
    assert "b" not in c


# --- LRU eviction ---

def test_eviction_when_over_capacity():
    c = LRUCacheWithTTL(capacity=2, default_ttl=60)
    c.set("a", 1)
    c.set("b", 2)
    c.set("c", 3)  # evicts "a" as LRU
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_marks_as_recently_used():
    c = LRUCacheWithTTL(capacity=2, default_ttl=60)
    c.set("a", 1)
    c.set("b", 2)
    _ = c.get("a")    # touch "a" → now "b" is LRU
    c.set("c", 3)     # evicts "b"
    assert c.get("a") == 1
    assert c.get("b") is None
    assert c.get("c") == 3


def test_set_existing_marks_as_recently_used():
    c = LRUCacheWithTTL(capacity=2, default_ttl=60)
    c.set("a", 1)
    c.set("b", 2)
    c.set("a", 11)    # update "a" → now "b" is LRU
    c.set("c", 3)     # evicts "b"
    assert c.get("a") == 11
    assert c.get("b") is None


def test_contains_does_not_affect_lru():
    c = LRUCacheWithTTL(capacity=2, default_ttl=60)
    c.set("a", 1)
    c.set("b", 2)
    assert "a" in c   # must NOT promote "a"
    c.set("c", 3)     # evicts "a" (still LRU)
    assert c.get("a") is None
    assert c.get("b") == 2


# --- TTL expiry ---

def test_expired_get_returns_none():
    clock = FakeClock()
    c = LRUCacheWithTTL(capacity=10, default_ttl=10, clock=clock)
    c.set("a", 1)
    clock.advance(15)
    assert c.get("a") is None


def test_not_yet_expired_get_returns_value():
    clock = FakeClock()
    c = LRUCacheWithTTL(capacity=10, default_ttl=10, clock=clock)
    c.set("a", 1)
    clock.advance(5)
    assert c.get("a") == 1


def test_per_entry_ttl_overrides_default():
    clock = FakeClock()
    c = LRUCacheWithTTL(capacity=10, default_ttl=100, clock=clock)
    c.set("short", "v", ttl=1)
    c.set("long", "v")
    clock.advance(2)
    assert c.get("short") is None
    assert c.get("long") == "v"


def test_exactly_at_ttl_is_expired():
    # boundary: at now == t + ttl, entry is expired
    clock = FakeClock()
    c = LRUCacheWithTTL(capacity=10, default_ttl=10, clock=clock)
    c.set("a", 1)
    clock.advance(10)
    assert c.get("a") is None


def test_negative_ttl_rejected():
    c = LRUCacheWithTTL(capacity=10, default_ttl=10)
    with pytest.raises(ValueError):
        c.set("a", 1, ttl=-5)


def test_zero_ttl_rejected_on_set():
    c = LRUCacheWithTTL(capacity=10, default_ttl=10)
    with pytest.raises(ValueError):
        c.set("a", 1, ttl=0)
