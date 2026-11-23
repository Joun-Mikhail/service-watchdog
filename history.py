"""Append check results to a CSV file and read them back for reporting."""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

FIELDS = ["timestamp", "name", "url", "status", "category", "status_code", "response_time_ms"]


def append(result, path, now=None):
    """Append one CheckResult as a CSV row, writing a header if the file is new."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    is_new = not os.path.exists(path) or os.path.getsize(path) == 0
    timestamp = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp": timestamp,
                "name": result.name,
                "url": result.url,
                "status": result.status,
                "category": result.category or "",
                "status_code": "" if result.status_code is None else result.status_code,
                "response_time_ms": "" if result.response_time_ms is None else result.response_time_ms,
            }
        )


def read(path, since=None):
    """Yield history rows as dicts, optionally only those at or after the datetime since."""
    if not os.path.exists(path):
        return
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["timestamp"] = datetime.fromisoformat(row["timestamp"])
            if since is None or row["timestamp"] >= since:
                yield row
