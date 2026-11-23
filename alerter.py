"""Build and send alert emails over SMTP (standard library only)."""

from __future__ import annotations

import smtplib
from datetime import datetime
from email.mime.text import MIMEText

from state import EVENT_DEGRADED, EVENT_DOWN

RUNBOOKS = {
    "DNS": "docs/runbooks/dns-failure.md",
    "TCP": "docs/runbooks/connection-failure.md",
    "TLS": "docs/runbooks/tls-certificate.md",
    "TLS_EXPIRING": "docs/runbooks/tls-certificate.md",
    "HTTP": "docs/runbooks/http-errors.md",
    "CONTENT": "docs/runbooks/http-errors.md",
    "LATENCY": "docs/runbooks/high-latency.md",
}


def format_downtime(seconds):
    """Format a duration in seconds as a short string such as '2h 15m 30s'."""
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def build_message(event):
    """Return (subject, body) for an Event."""
    r = event.result
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if event.kind == EVENT_DOWN:
        subject = f"[DOWN] {r.name} - {r.category} failure"
        headline = "Service is DOWN"
    elif event.kind == EVENT_DEGRADED:
        subject = f"[DEGRADED] {r.name} - {r.category}"
        headline = "Service is DEGRADED"
    else:
        subject = f"[RECOVERED] {r.name} - back up after {format_downtime(event.downtime_seconds)}"
        headline = "Service has RECOVERED"

    lines = [
        headline,
        "",
        f"Service:     {r.name}",
        f"URL:         {r.url}",
        f"Time:        {timestamp}",
    ]
    if r.category:
        lines.append(f"Failure:     {r.category}")
    if r.detail:
        lines.append(f"Detail:      {r.detail}")
    if r.ip:
        lines.append(f"Resolved IP: {r.ip}")
    if r.status_code is not None:
        lines.append(f"HTTP status: {r.status_code}")
    if r.response_time_ms is not None:
        lines.append(f"Latency:     {r.response_time_ms} ms")
    if r.tls_days_left is not None:
        lines.append(f"TLS expiry:  {r.tls_days_left} days")
    if event.downtime_seconds is not None:
        lines.append(f"Downtime:    {format_downtime(event.downtime_seconds)}")
    if r.category in RUNBOOKS:
        lines += ["", f"Runbook:     {RUNBOOKS[r.category]}"]
    lines += ["", "-- service-watchdog"]

    return subject, "\n".join(lines)


def send_email(smtp_server, smtp_port, sender, password, recipient, subject, body):
    """Send a plain-text email using SMTP with STARTTLS."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
