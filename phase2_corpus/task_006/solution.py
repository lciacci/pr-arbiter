"""Reference solution for task_006."""
import time


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float, clock=None):
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if refill_rate <= 0:
            raise ValueError("refill_rate must be > 0")
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.clock = clock if clock is not None else time.monotonic
        self._tokens = self.capacity
        self._last_refill = self.clock()

    def _refill(self) -> None:
        now = self.clock()
        elapsed = now - self._last_refill
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
            self._last_refill = now

    def try_consume(self, tokens: float = 1.0) -> bool:
        if tokens <= 0:
            raise ValueError("tokens must be > 0")
        self._refill()
        if tokens > self._tokens:
            return False
        self._tokens -= tokens
        return True

    def tokens_available(self) -> float:
        self._refill()
        return self._tokens
