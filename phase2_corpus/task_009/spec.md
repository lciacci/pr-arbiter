# Task 009 — Bounded-time event scheduler

Difficulty: **hard**
Style: hand-authored

## Class to implement

```python
class Scheduler:
    def __init__(self, clock=None): ...
    def schedule(self, when: float, callback, *args, **kwargs) -> int: ...
    def cancel(self, event_id: int) -> bool: ...
    def run_until(self, deadline: float) -> int: ...
    def time(self) -> float: ...
```

## Specification

A single-threaded event scheduler that fires callbacks at scheduled
times, deterministically and in order.

### Constructor
- `clock`: optional zero-argument callable returning current time as a float.
  Defaults to `time.monotonic`.

### schedule(when, callback, *args, **kwargs)
- Schedule `callback(*args, **kwargs)` to fire at absolute time `when`
  (in seconds, on the scheduler's clock).
- Returns a unique positive integer `event_id` that can be passed to `cancel`.
- Event IDs must be monotonically increasing across the scheduler's lifetime.
- `when` may be in the past — in that case, the event fires on the next
  `run_until` call.
- `callback` may itself call `schedule()` or `cancel()` from within its
  body. Events scheduled by a callback for a time at or before the
  current run's deadline must fire in the same `run_until` invocation
  if their `when` is at or before the current scheduler time.

### cancel(event_id)
- Cancels a pending event. Returns `True` if the event was pending and
  is now cancelled, `False` if it was already fired, already cancelled,
  or never existed.

### run_until(deadline)
- Advances the scheduler, firing all pending events with `when <= deadline`
  in order of their scheduled `when` (ties broken by event_id, which
  preserves schedule order).
- Returns the number of events fired during this call.
- Updates the scheduler's notion of time as it fires events. Specifically,
  before each callback is invoked, `self.time()` reflects the event's
  scheduled `when` time, not the clock's current value.
  (This makes scheduling deterministic regardless of how long callbacks
  take to execute.)
- After all eligible events have fired, the scheduler's time advances to
  `deadline`.
- An event whose `when > deadline` is NOT fired and remains pending for
  a future `run_until`.

### time()
- Returns the scheduler's current notion of time as a float.
- Before any `run_until` call, this equals `clock()` at construction time.

### Examples

```
s = Scheduler(clock=fake_clock)
log = []
s.schedule(when=10.0, callback=lambda: log.append("a"))
s.schedule(when=5.0, callback=lambda: log.append("b"))
s.run_until(deadline=20.0)
# log == ["b", "a"]   (fired in time order)
# s.time() == 20.0
```

## Out of scope

- Real-time blocking (we don't sleep — we just advance the clock notion).
- Recurring events.
- Priority-on-tie beyond event_id.
- Thread safety.
