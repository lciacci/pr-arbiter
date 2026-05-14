# Task 006 — Token bucket rate limiter

Difficulty: **medium**
Style: hand-authored

## Class to implement

```python
class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float, clock=None): ...
    def try_consume(self, tokens: float = 1.0) -> bool: ...
    def tokens_available(self) -> float: ...
```

## Specification

Implement a token-bucket rate limiter. The bucket holds up to `capacity`
tokens. Tokens accrue continuously at `refill_rate` tokens per second up
to the cap. `try_consume(n)` succeeds (and deducts `n` tokens) only if
the bucket currently holds at least `n` tokens.

### Constructor
- `capacity`: positive float, the bucket's maximum.
- `refill_rate`: positive float, tokens added per second.
- `clock`: optional zero-argument callable returning current time in seconds.
  Defaults to `time.monotonic`. Used to make refill deterministic in tests.
- The bucket starts **full** (with `capacity` tokens).
- Raise `ValueError` if `capacity <= 0` or `refill_rate <= 0`.

### try_consume(tokens=1.0)
- If enough tokens are available, deduct them and return `True`.
- Otherwise return `False` without deducting anything (atomic: either
  consume in full or not at all).
- Raise `ValueError` if `tokens <= 0`.
- It is fine for `tokens` to be a float (e.g., 0.5 tokens).
- A request for more tokens than the bucket's capacity always returns
  `False` (it can never succeed). Do NOT raise.

### tokens_available()
- Returns the current token count as a float. Always refresh from the
  clock before returning — the bucket continuously accrues tokens.
- The value never exceeds `capacity`.
- The value never goes below 0.

### Refill semantics
- Refill is **continuous**. If `refill_rate = 10/sec` and `0.5 seconds`
  pass, the bucket gains 5 tokens (capped at `capacity`).
- Refill happens lazily — only when `try_consume` or `tokens_available`
  is called. You do not need a background thread.
- The clock is monotonic and never goes backward.

### Examples

- Bucket of capacity 5, rate 1/sec. Start full.
  - `try_consume(3)` → True. 2 tokens remain.
  - Immediately `try_consume(3)` → False. 2 tokens remain (no deduction).
  - Advance clock by 2 seconds. `tokens_available()` → 4.0.
  - `try_consume(4)` → True. 0 tokens remain.

## Out of scope

- Thread safety
- Async support
- Bursting beyond capacity (capacity is a hard ceiling)
- Negative tokens or "borrowing" against future refills
