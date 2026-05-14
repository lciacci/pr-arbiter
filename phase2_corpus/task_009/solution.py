"""Reference solution for task_009."""
import heapq
import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class _Event:
    when: float
    event_id: int
    callback: Callable = field(compare=False)
    args: tuple = field(compare=False, default_factory=tuple)
    kwargs: dict = field(compare=False, default_factory=dict)
    cancelled: bool = field(compare=False, default=False)


class Scheduler:
    def __init__(self, clock=None):
        self._clock = clock if clock is not None else time.monotonic
        self._time = self._clock()
        self._heap: list[_Event] = []
        self._next_id = 1
        self._events: dict[int, _Event] = {}

    def schedule(self, when: float, callback, *args, **kwargs) -> int:
        ev = _Event(
            when=when,
            event_id=self._next_id,
            callback=callback,
            args=args,
            kwargs=kwargs,
        )
        self._next_id += 1
        heapq.heappush(self._heap, ev)
        self._events[ev.event_id] = ev
        return ev.event_id

    def cancel(self, event_id: int) -> bool:
        ev = self._events.get(event_id)
        if ev is None or ev.cancelled:
            return False
        ev.cancelled = True
        return True

    def run_until(self, deadline: float) -> int:
        fired = 0
        while self._heap and self._heap[0].when <= deadline:
            ev = heapq.heappop(self._heap)
            if ev.cancelled:
                self._events.pop(ev.event_id, None)
                continue
            # Advance scheduler time to the event's scheduled when
            self._time = ev.when
            ev.callback(*ev.args, **ev.kwargs)
            self._events.pop(ev.event_id, None)
            fired += 1
        self._time = deadline
        return fired

    def time(self) -> float:
        return self._time
