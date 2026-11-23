"""End-to-end checks against real local services from demo/lab.py."""

import shutil
import socket

import pytest

from config import Target
from demo import lab
from monitor import DEGRADED, DOWN, UP, check_target


@pytest.fixture(scope="module")
def services():
    urls, stop = lab.start({name: 0 for name in lab.DEFAULT_PORTS})
    yield urls
    stop()


def check(url, **kwargs):
    return check_target(Target(name="t", url=url, **kwargs), timeout=3)


def test_healthy_service(services):
    result = check(services["healthy"], keyword="Welcome", max_latency_ms=1000)
    assert result.status == UP
    assert result.status_code == 200


def test_server_error(services):
    result = check(services["error"])
    assert (result.status, result.category, result.status_code) == (DOWN, "HTTP", 503)


def test_slow_service(services):
    result = check(services["slow"], max_latency_ms=500)
    assert (result.status, result.category) == (DEGRADED, "LATENCY")


def test_maintenance_page(services):
    result = check(services["maintenance"], keyword="Welcome")
    assert (result.status, result.category) == (DOWN, "CONTENT")


def test_flaky_service_recovers(services):
    statuses = [check(services["flaky"]).status for _ in range(lab.LabHandler.flaky_failures + 1)]
    assert statuses == [DOWN] * lab.LabHandler.flaky_failures + [UP]


@pytest.mark.skipif(not shutil.which("openssl"), reason="openssl not installed")
def test_untrusted_certificate(services):
    result = check(services["tls"])
    assert (result.status, result.category) == (DOWN, "TLS")
    assert "certificate verification failed" in result.detail


def test_stopped_service():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    result = check(f"http://127.0.0.1:{port}/")
    assert (result.status, result.category) == (DOWN, "TCP")
