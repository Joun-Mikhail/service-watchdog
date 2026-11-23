import logging
import sys
import types

import alerter
import watchdog
from config import Settings
from monitor import DOWN, CheckResult
from state import EVENT_DOWN, Event

TOPIC = "arn:aws:sns:eu-central-1:123456789012:service-watchdog-alerts"


def down_event():
    r = CheckResult(name="API", url="https://api.example.com", status=DOWN, category="TCP", detail="refused")
    return Event(EVENT_DOWN, r)


def make_notifier(monkeypatch, email=None, sns=None, dry_run=False):
    calls = []
    monkeypatch.setattr(watchdog, "send_email", lambda *a: calls.append(("email", a[-2])))
    monkeypatch.setattr(watchdog, "publish_sns", lambda *a: calls.append(("sns", a[-2])))
    notifier = watchdog.Notifier(Settings(), logging.getLogger("test"), email, sns, dry_run)
    return notifier, calls


def test_sends_to_every_configured_channel(monkeypatch):
    notifier, calls = make_notifier(monkeypatch, email=("a@x", "pw", "b@x"), sns=TOPIC)
    notifier.send(down_event())

    assert notifier.channels == ["email", "sns"]
    assert calls == [("email", "[DOWN] API - TCP failure"), ("sns", "[DOWN] API - TCP failure")]


def test_dry_run_sends_nothing(monkeypatch):
    notifier, calls = make_notifier(monkeypatch, email=("a@x", "pw", "b@x"), sns=TOPIC, dry_run=True)
    notifier.send(down_event())
    assert calls == []


def test_one_failing_channel_does_not_block_the_other(monkeypatch, caplog):
    notifier, calls = make_notifier(monkeypatch, email=("a@x", "pw", "b@x"), sns=TOPIC)

    def broken(*args):
        raise OSError("smtp unreachable")

    monkeypatch.setattr(watchdog, "send_email", broken)
    with caplog.at_level(logging.ERROR):
        notifier.send(down_event())

    assert calls == [("sns", "[DOWN] API - TCP failure")]
    assert "smtp unreachable" in caplog.text


def test_from_env_reads_sns_topic(monkeypatch):
    for key in ("SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("ALERT_SNS_TOPIC_ARN", TOPIC)

    notifier = watchdog.Notifier.from_env(Settings(), logging.getLogger("test"))
    assert notifier.channels == ["sns"]


def test_publish_sns_uses_topic_region_and_safe_subject(monkeypatch):
    published = {}

    class FakeClient:
        def publish(self, **kwargs):
            published.update(kwargs)

    fake_boto3 = types.SimpleNamespace(
        client=lambda service, region_name: (
            published.update(service=service, region=region_name) or FakeClient()
        )
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    alerter.publish_sns(TOPIC, "[DOWN] Café " + "x" * 200, "body")

    assert published["service"] == "sns"
    assert published["region"] == "eu-central-1"
    assert published["TopicArn"] == TOPIC
    assert published["Subject"].startswith("[DOWN] Caf? ")
    assert len(published["Subject"]) < 100
    assert published["Message"] == "body"
