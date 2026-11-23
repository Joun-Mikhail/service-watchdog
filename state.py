"""Track each target's health over time and decide when to alert.

A target is only reported DOWN after `failure_threshold` consecutive failures,
which keeps a single network blip from paging anyone.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from monitor import DEGRADED, DOWN

EVENT_DOWN = "DOWN"
EVENT_DEGRADED = "DEGRADED"
EVENT_RECOVERED = "RECOVERED"


@dataclass
class Event:
    """A state change that should be alerted on."""

    kind: str
    result: object
    downtime_seconds: Optional[float] = None


@dataclass
class TargetState:
    """Health history for one target."""

    consecutive_failures: int = 0
    first_failure_at: Optional[float] = None
    alerted_down: bool = False
    degraded: bool = False


class StateTracker:
    """Turn a stream of CheckResults into alertable Events."""

    def __init__(self, failure_threshold=2, clock=time.time):
        """Create a tracker; clock is injectable for testing."""
        self.failure_threshold = failure_threshold
        self.clock = clock
        self.targets = {}

    def update(self, result):
        """Record a CheckResult and return an Event if one should be sent, else None."""
        state = self.targets.setdefault(result.url, TargetState())
        now = self.clock()

        if result.status == DOWN:
            state.consecutive_failures += 1
            if state.first_failure_at is None:
                state.first_failure_at = now
            if state.consecutive_failures >= self.failure_threshold and not state.alerted_down:
                state.alerted_down = True
                return Event(EVENT_DOWN, result)
            return None

        event = None
        if state.alerted_down:
            event = Event(EVENT_RECOVERED, result, now - state.first_failure_at)
        state.consecutive_failures = 0
        state.first_failure_at = None
        state.alerted_down = False

        was_degraded, state.degraded = state.degraded, result.status == DEGRADED
        if event is None and state.degraded and not was_degraded:
            event = Event(EVENT_DEGRADED, result)
        return event
