"""Tests for TokenBucket."""
import pytest
from solution import TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.t = start
    def __call__(self) -> float:
        return self.t
    def advance(self, seconds: float):
        self.t += seconds


# --- construction ---

def test_starts_full():
    b = TokenBucket(capacity=5, refill_rate=1)
    assert b.tokens_available() == 5.0


def test_zero_capacity_rejected():
    with pytest.raises(ValueError):
        TokenBucket(capacity=0, refill_rate=1)


def test_negative_rate_rejected():
    with pytest.raises(ValueError):
        TokenBucket(capacity=5, refill_rate=-1)


# --- try_consume ---

def test_consume_within_capacity():
    b = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
    assert b.try_consume(3) is True
    assert b.tokens_available() == 2.0


def test_consume_more_than_available_fails():
    b = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
    b.try_consume(3)
    assert b.try_consume(3) is False
    # No deduction on failed consume
    assert b.tokens_available() == 2.0


def test_consume_more_than_capacity_always_fails():
    b = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
    assert b.try_consume(10) is False
    assert b.tokens_available() == 5.0


def test_consume_zero_rejected():
    b = TokenBucket(capacity=5, refill_rate=1)
    with pytest.raises(ValueError):
        b.try_consume(0)


def test_consume_negative_rejected():
    b = TokenBucket(capacity=5, refill_rate=1)
    with pytest.raises(ValueError):
        b.try_consume(-1)


def test_fractional_tokens():
    b = TokenBucket(capacity=5, refill_rate=1, clock=FakeClock())
    assert b.try_consume(0.5) is True
    assert b.tokens_available() == pytest.approx(4.5)


# --- refill ---

def test_refill_over_time():
    clock = FakeClock()
    b = TokenBucket(capacity=10, refill_rate=2, clock=clock)
    b.try_consume(10)  # empty
    assert b.tokens_available() == 0.0
    clock.advance(3)   # +6 tokens
    assert b.tokens_available() == pytest.approx(6.0)


def test_refill_caps_at_capacity():
    clock = FakeClock()
    b = TokenBucket(capacity=10, refill_rate=2, clock=clock)
    b.try_consume(10)
    clock.advance(100)  # would add 200 tokens, but cap is 10
    assert b.tokens_available() == 10.0


def test_continuous_refill_fractional():
    clock = FakeClock()
    b = TokenBucket(capacity=10, refill_rate=10, clock=clock)
    b.try_consume(10)
    clock.advance(0.5)
    assert b.tokens_available() == pytest.approx(5.0)


def test_consume_after_partial_refill():
    clock = FakeClock()
    b = TokenBucket(capacity=5, refill_rate=1, clock=clock)
    b.try_consume(5)
    clock.advance(2)  # +2 tokens
    assert b.try_consume(2) is True
    assert b.tokens_available() == pytest.approx(0.0)


def test_tokens_available_does_not_consume():
    clock = FakeClock()
    b = TokenBucket(capacity=5, refill_rate=1, clock=clock)
    _ = b.tokens_available()
    _ = b.tokens_available()
    assert b.tokens_available() == 5.0


def test_full_scenario_from_spec():
    clock = FakeClock()
    b = TokenBucket(capacity=5, refill_rate=1, clock=clock)
    assert b.try_consume(3) is True
    assert b.try_consume(3) is False
    clock.advance(2)
    assert b.tokens_available() == pytest.approx(4.0)
    assert b.try_consume(4) is True
    assert b.tokens_available() == pytest.approx(0.0)
