"""Layer-by-layer network diagnostics: DNS, TCP, then TLS.

Each check raises DiagnosticError with a category so a failure can be traced
to the layer where it happened instead of a generic "site is down".
"""

from __future__ import annotations

import socket
import ssl
import time


class DiagnosticError(Exception):
    """A failed diagnostic step, tagged with the layer that failed."""

    def __init__(self, category, detail):
        """Store the failure category (DNS, TCP, TLS) and a readable detail."""
        super().__init__(f"{category}: {detail}")
        self.category = category
        self.detail = detail


def resolve_dns(host, port):
    """Resolve host and return its first IP address.

    Raises:
        DiagnosticError: category DNS when the name cannot be resolved.
    """
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise DiagnosticError("DNS", f"could not resolve {host}: {e.strerror}") from e
    return infos[0][4][0]


def check_tcp(ip, port, timeout):
    """Open and close a TCP connection to ip:port.

    Raises:
        DiagnosticError: category TCP when the port is refused, filtered or unreachable.
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            pass
    except socket.timeout as e:
        raise DiagnosticError("TCP", f"connection to {ip}:{port} timed out after {timeout}s") from e
    except ConnectionRefusedError as e:
        raise DiagnosticError("TCP", f"connection to {ip}:{port} refused") from e
    except OSError as e:
        raise DiagnosticError("TCP", f"cannot reach {ip}:{port}: {e.strerror or e}") from e


def check_tls(host, port, timeout):
    """Perform a TLS handshake and return the days left on the certificate.

    Raises:
        DiagnosticError: category TLS when the handshake or certificate validation fails.
    """
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except ssl.SSLCertVerificationError as e:
        raise DiagnosticError("TLS", f"certificate verification failed: {e.verify_message}") from e
    except (ssl.SSLError, socket.timeout, OSError) as e:
        raise DiagnosticError("TLS", f"TLS handshake with {host}:{port} failed: {e}") from e

    expires_at = ssl.cert_time_to_seconds(cert["notAfter"])
    return int((expires_at - time.time()) // 86400)
