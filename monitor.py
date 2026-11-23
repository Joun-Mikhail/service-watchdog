"""Run a full health check against one target and classify the result."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests

import diagnostics

UP = "UP"
DEGRADED = "DEGRADED"
DOWN = "DOWN"


@dataclass
class CheckResult:
    """Outcome of a single check."""

    name: str
    url: str
    status: str
    category: Optional[str] = None
    detail: str = ""
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    ip: Optional[str] = None
    tls_days_left: Optional[int] = None

    def log_line(self):
        """Return the result as a key=value line that is easy to grep or query."""
        fields = {
            "status": self.status,
            "name": self.name,
            "url": self.url,
            "category": self.category,
            "code": self.status_code,
            "latency_ms": self.response_time_ms,
            "ip": self.ip,
            "tls_days": self.tls_days_left,
        }
        line = " ".join(f"{k}={v}" for k, v in fields.items() if v is not None)
        if self.detail:
            line += f' detail="{self.detail}"'
        return line


def check_target(target, timeout=10, tls_warning_days=14):
    """Check a target layer by layer (DNS, TCP, TLS, HTTP) and return a CheckResult."""
    parsed = urlparse(target.url)
    is_https = parsed.scheme == "https"
    host = parsed.hostname
    port = parsed.port or (443 if is_https else 80)
    result = CheckResult(name=target.name, url=target.url, status=UP)

    try:
        result.ip = diagnostics.resolve_dns(host, port)
        diagnostics.check_tcp(result.ip, port, timeout)
        if is_https:
            result.tls_days_left = diagnostics.check_tls(host, port, timeout)
    except diagnostics.DiagnosticError as e:
        result.status, result.category, result.detail = DOWN, e.category, e.detail
        return result

    start = time.perf_counter()
    try:
        response = requests.get(target.url, timeout=timeout)
    except requests.Timeout:
        result.status, result.category = DOWN, "HTTP"
        result.detail = f"no HTTP response within {timeout}s"
        return result
    except requests.RequestException as e:
        result.status, result.category, result.detail = DOWN, "HTTP", str(e)
        return result
    result.response_time_ms = round((time.perf_counter() - start) * 1000, 1)
    result.status_code = response.status_code

    if response.status_code != target.expected_status:
        result.status, result.category = DOWN, "HTTP"
        result.detail = f"expected status {target.expected_status}, got {response.status_code}"
    elif target.keyword and target.keyword not in response.text:
        result.status, result.category = DOWN, "CONTENT"
        result.detail = f"keyword {target.keyword!r} not found in response body"
    elif target.max_latency_ms and result.response_time_ms > target.max_latency_ms:
        result.status, result.category = DEGRADED, "LATENCY"
        result.detail = f"{result.response_time_ms}ms exceeds limit of {target.max_latency_ms}ms"
    elif result.tls_days_left is not None and result.tls_days_left < tls_warning_days:
        result.status, result.category = DEGRADED, "TLS_EXPIRING"
        result.detail = f"certificate expires in {result.tls_days_left} days"

    return result
