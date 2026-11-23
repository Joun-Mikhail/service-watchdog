import socket

import pytest

import diagnostics
from diagnostics import DiagnosticError


def test_dns_failure_is_categorised(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    monkeypatch.setattr(diagnostics.socket, "getaddrinfo", fail)

    with pytest.raises(DiagnosticError) as exc:
        diagnostics.resolve_dns("missing.invalid", 443)
    assert exc.value.category == "DNS"


def test_refused_port_is_categorised():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    with pytest.raises(DiagnosticError) as exc:
        diagnostics.check_tcp("127.0.0.1", port, timeout=2)
    assert exc.value.category == "TCP"
    assert "refused" in exc.value.detail


def test_open_port_passes():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        diagnostics.check_tcp("127.0.0.1", server.getsockname()[1], timeout=2)
