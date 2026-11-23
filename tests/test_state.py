from monitor import DEGRADED, DOWN, UP, CheckResult
from state import EVENT_DEGRADED, EVENT_DOWN, EVENT_RECOVERED, StateTracker


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def result(status):
    return CheckResult(name="site", url="https://example.com", status=status)


def test_alerts_only_after_threshold_and_only_once():
    tracker = StateTracker(failure_threshold=3)

    assert tracker.update(result(DOWN)) is None
    assert tracker.update(result(DOWN)) is None
    assert tracker.update(result(DOWN)).kind == EVENT_DOWN
    assert tracker.update(result(DOWN)) is None


def test_single_blip_does_not_alert_or_recover():
    tracker = StateTracker(failure_threshold=2)

    assert tracker.update(result(DOWN)) is None
    assert tracker.update(result(UP)) is None


def test_recovery_reports_downtime_from_first_failure():
    clock = Clock()
    tracker = StateTracker(failure_threshold=2, clock=clock)

    tracker.update(result(DOWN))
    clock.now += 300
    assert tracker.update(result(DOWN)).kind == EVENT_DOWN
    clock.now += 300
    event = tracker.update(result(UP))

    assert event.kind == EVENT_RECOVERED
    assert event.downtime_seconds == 600


def test_degraded_alerts_once_per_episode():
    tracker = StateTracker()

    assert tracker.update(result(DEGRADED)).kind == EVENT_DEGRADED
    assert tracker.update(result(DEGRADED)) is None
    assert tracker.update(result(UP)) is None
    assert tracker.update(result(DEGRADED)).kind == EVENT_DEGRADED
