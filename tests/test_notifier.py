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


def test_template_credentials_are_treated_as_unset(monkeypatch):
    monkeypatch.setenv("SENDER_EMAIL", "your-email@gmail.com")
    monkeypatch.setenv("SENDER_PASSWORD", "your-app-password")
    monkeypatch.setenv("RECIPIENT_EMAIL", "alert-recipient@example.com")
    assert watchdog.email_credentials() is None


def test_real_credentials_are_used(monkeypatch):
    monkeypatch.setenv("SENDER_EMAIL", "ops@company.test")
    monkeypatch.setenv("SENDER_PASSWORD", "s3cret")
    monkeypatch.setenv("RECIPIENT_EMAIL", "oncall@company.test")
    assert watchdog.email_credentials() == ("ops@company.test", "s3cret", "oncall@company.test")


def test_send_email_uses_starttls_and_login(monkeypatch):
    actions = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            actions.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            actions.append(("quit",))

        def starttls(self):
            actions.append(("starttls",))

        def login(self, user, password):
            actions.append(("login", user))

        def send_message(self, msg):
            actions.append(("send", msg["To"], msg["Subject"]))

    monkeypatch.setattr(alerter.smtplib, "SMTP", FakeSMTP)
    alerter.send_email("smtp.test", 587, "ops@company.test", "pw", "oncall@company.test", "Subject", "Body")

    assert actions == [
        ("connect", "smtp.test", 587),
        ("starttls",),
        ("login", "ops@company.test"),
        ("send", "oncall@company.test", "Subject"),
        ("quit",),
    ]
