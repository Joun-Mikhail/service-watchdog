import pytest

from alerter import build_message, format_downtime
from monitor import DOWN, UP, CheckResult
from state import EVENT_DOWN, EVENT_RECOVERED, Event


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (45, "45s"),
        (301, "5m 1s"),
        (8130, "2h 15m 30s"),
        (3600, "1h 0s"),
    ],
)
def test_format_downtime(seconds, expected):
    assert format_downtime(seconds) == expected


def test_down_message_includes_diagnosis_and_runbook():
    r = CheckResult(
        name="API",
        url="https://api.example.com",
        status=DOWN,
        category="DNS",
        detail="could not resolve api.example.com",
    )
    subject, body = build_message(Event(EVENT_DOWN, r))

    assert subject == "[DOWN] API - DNS failure"
    assert "could not resolve api.example.com" in body
    assert "docs/runbooks/dns-failure.md" in body


def test_recovery_message_includes_downtime():
    r = CheckResult(name="API", url="https://api.example.com", status=UP, status_code=200)
    subject, body = build_message(Event(EVENT_RECOVERED, r, downtime_seconds=301))

    assert subject == "[RECOVERED] API - back up after 5m 1s"
    assert "Downtime:    5m 1s" in body


def test_every_runbook_linked_from_alerts_exists():
    from pathlib import Path

    from alerter import RUNBOOKS

    root = Path(__file__).resolve().parents[1]
    missing = [path for path in set(RUNBOOKS.values()) if not (root / path).is_file()]
    assert missing == []
