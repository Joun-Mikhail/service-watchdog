import pytest
import requests

import diagnostics
import monitor
from config import Target
from monitor import DEGRADED, DOWN, UP, check_target


class FakeResponse:
    def __init__(self, status_code=200, text="hello world"):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def healthy_network(monkeypatch):
    monkeypatch.setattr(diagnostics, "resolve_dns", lambda host, port: "203.0.113.10")
    monkeypatch.setattr(diagnostics, "check_tcp", lambda ip, port, timeout: None)
    monkeypatch.setattr(diagnostics, "check_tls", lambda host, port, timeout: 90)


def respond_with(monkeypatch, response=None, exc=None):
    def fake_get(url, timeout):
        if exc:
            raise exc
        return response

    monkeypatch.setattr(monitor.requests, "get", fake_get)


def test_healthy_target_is_up(healthy_network, monkeypatch):
    respond_with(monkeypatch, FakeResponse())
    result = check_target(Target(name="site", url="https://example.com"))

    assert result.status == UP
    assert result.ip == "203.0.113.10"
    assert result.tls_days_left == 90
    assert result.status_code == 200


def test_dns_failure_stops_further_checks(monkeypatch):
    def fail(host, port):
        raise diagnostics.DiagnosticError("DNS", "could not resolve")

    monkeypatch.setattr(diagnostics, "resolve_dns", fail)
    respond_with(monkeypatch, exc=AssertionError("HTTP should not be attempted"))

    result = check_target(Target(name="site", url="https://example.com"))

    assert (result.status, result.category) == (DOWN, "DNS")


def test_tcp_failure_is_reported(healthy_network, monkeypatch):
    def refuse(ip, port, timeout):
        raise diagnostics.DiagnosticError("TCP", "refused")

    monkeypatch.setattr(diagnostics, "check_tcp", refuse)

    result = check_target(Target(name="site", url="https://example.com"))

    assert (result.status, result.category) == (DOWN, "TCP")


def test_tls_not_checked_for_plain_http(healthy_network, monkeypatch):
    def boom(host, port, timeout):
        raise AssertionError("TLS should not be checked for http://")

    monkeypatch.setattr(diagnostics, "check_tls", boom)
    respond_with(monkeypatch, FakeResponse())

    assert check_target(Target(name="site", url="http://example.com")).status == UP


def test_unexpected_status_code(healthy_network, monkeypatch):
    respond_with(monkeypatch, FakeResponse(status_code=503))
    result = check_target(Target(name="site", url="https://example.com"))

    assert (result.status, result.category) == (DOWN, "HTTP")
    assert "got 503" in result.detail


def test_http_timeout(healthy_network, monkeypatch):
    respond_with(monkeypatch, exc=requests.Timeout())
    result = check_target(Target(name="site", url="https://example.com"), timeout=5)

    assert (result.status, result.category) == (DOWN, "HTTP")
    assert "5s" in result.detail


def test_missing_keyword(healthy_network, monkeypatch):
    respond_with(monkeypatch, FakeResponse(text="maintenance page"))
    result = check_target(Target(name="site", url="https://example.com", keyword="Welcome"))

    assert (result.status, result.category) == (DOWN, "CONTENT")


def test_slow_response_is_degraded(healthy_network, monkeypatch):
    respond_with(monkeypatch, FakeResponse())
    ticks = iter([0.0, 2.5])
    monkeypatch.setattr(monitor.time, "perf_counter", lambda: next(ticks))

    result = check_target(Target(name="site", url="https://example.com", max_latency_ms=1000))

    assert (result.status, result.category) == (DEGRADED, "LATENCY")
    assert result.response_time_ms == 2500


def test_expiring_certificate_is_degraded(healthy_network, monkeypatch):
    monkeypatch.setattr(diagnostics, "check_tls", lambda host, port, timeout: 3)
    respond_with(monkeypatch, FakeResponse())

    result = check_target(Target(name="site", url="https://example.com"), tls_warning_days=14)

    assert (result.status, result.category) == (DEGRADED, "TLS_EXPIRING")


def test_log_line_is_key_value():
    result = monitor.CheckResult(
        name="api", url="https://x", status=DOWN, category="DNS", detail="no such host"
    )
    assert result.log_line() == 'status=DOWN name=api url=https://x category=DNS detail="no such host"'
