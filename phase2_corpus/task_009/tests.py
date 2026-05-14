"""Tests for Scheduler."""
import pytest
from solution import Scheduler


class FakeClock:
    def __init__(self, start: float = 0.0):
        self.t = start
    def __call__(self) -> float:
        return self.t


def test_schedule_returns_unique_ids():
    s = Scheduler(clock=FakeClock())
    a = s.schedule(1.0, lambda: None)
    b = s.schedule(2.0, lambda: None)
    c = s.schedule(3.0, lambda: None)
    assert a != b != c
    assert b > a and c > b  # monotonic


def test_runs_in_time_order():
    s = Scheduler(clock=FakeClock())
    log = []
    s.schedule(10.0, lambda: log.append("a"))
    s.schedule(5.0, lambda: log.append("b"))
    s.run_until(20.0)
    assert log == ["b", "a"]


def test_returns_fire_count():
    s = Scheduler(clock=FakeClock())
    s.schedule(1.0, lambda: None)
    s.schedule(2.0, lambda: None)
    s.schedule(3.0, lambda: None)
    assert s.run_until(2.5) == 2


def test_events_past_deadline_stay_pending():
    s = Scheduler(clock=FakeClock())
    log = []
    s.schedule(10.0, lambda: log.append("a"))
    s.schedule(20.0, lambda: log.append("b"))
    s.run_until(15.0)
    assert log == ["a"]
    s.run_until(25.0)
    assert log == ["a", "b"]


def test_time_advances_to_deadline():
    s = Scheduler(clock=FakeClock())
    s.run_until(50.0)
    assert s.time() == 50.0


def test_time_during_callback_reflects_scheduled_when():
    s = Scheduler(clock=FakeClock())
    seen_times = []
    s.schedule(10.0, lambda: seen_times.append(s.time()))
    s.schedule(15.0, lambda: seen_times.append(s.time()))
    s.run_until(20.0)
    assert seen_times == [10.0, 15.0]


def test_cancel_pending_event():
    s = Scheduler(clock=FakeClock())
    log = []
    eid = s.schedule(10.0, lambda: log.append("a"))
    assert s.cancel(eid) is True
    s.run_until(20.0)
    assert log == []


def test_cancel_already_fired_returns_false():
    s = Scheduler(clock=FakeClock())
    eid = s.schedule(5.0, lambda: None)
    s.run_until(10.0)
    assert s.cancel(eid) is False


def test_cancel_unknown_event_returns_false():
    s = Scheduler(clock=FakeClock())
    assert s.cancel(99999) is False


def test_cancel_twice_second_returns_false():
    s = Scheduler(clock=FakeClock())
    eid = s.schedule(5.0, lambda: None)
    s.cancel(eid)
    assert s.cancel(eid) is False


def test_past_event_fires_on_next_run():
    clock = FakeClock(start=100.0)
    s = Scheduler(clock=clock)
    log = []
    s.schedule(50.0, lambda: log.append("past"))  # scheduled in the past
    s.run_until(110.0)
    assert log == ["past"]


def test_callback_can_schedule_new_event_in_same_run():
    s = Scheduler(clock=FakeClock())
    log = []

    def first():
        log.append("first")
        s.schedule(8.0, lambda: log.append("second"))

    s.schedule(5.0, first)
    s.run_until(10.0)
    assert log == ["first", "second"]


def test_callback_scheduling_past_deadline_stays_pending():
    s = Scheduler(clock=FakeClock())
    log = []

    def first():
        log.append("first")
        s.schedule(50.0, lambda: log.append("future"))  # past deadline

    s.schedule(5.0, first)
    fired = s.run_until(10.0)
    assert log == ["first"]
    assert fired == 1


def test_ties_broken_by_schedule_order():
    s = Scheduler(clock=FakeClock())
    log = []
    s.schedule(5.0, lambda: log.append("first"))
    s.schedule(5.0, lambda: log.append("second"))
    s.schedule(5.0, lambda: log.append("third"))
    s.run_until(10.0)
    assert log == ["first", "second", "third"]


def test_callback_with_args_and_kwargs():
    s = Scheduler(clock=FakeClock())
    log = []
    s.schedule(1.0, lambda x, y: log.append((x, y)), 10, y=20)
    s.run_until(2.0)
    assert log == [(10, 20)]


def test_callback_can_cancel_other_pending():
    s = Scheduler(clock=FakeClock())
    log = []
    pending_id = None

    def first():
        log.append("first")
        s.cancel(pending_id)

    s.schedule(5.0, first)
    pending_id = s.schedule(8.0, lambda: log.append("should_not_fire"))
    s.run_until(10.0)
    assert log == ["first"]
