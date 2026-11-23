"""Summarise check history into an uptime report (text table and optional HTML).

Usage:
    python report.py                       # last 24 hours, printed as a table
    python report.py --hours 168 --html reports/weekly.html
"""

from __future__ import annotations

import argparse
import html
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import history

HEALTHY = {"UP", "DEGRADED"}


@dataclass
class TargetSummary:
    """Aggregated statistics for one target over the report window."""

    name: str
    url: str
    checks: int = 0
    healthy: int = 0
    degraded: int = 0
    incidents: int = 0
    latencies: list = field(default_factory=list)
    failure_categories: Counter = field(default_factory=Counter)
    _last_status: str = ""

    @property
    def uptime_pct(self):
        """Share of checks where the target was reachable (UP or DEGRADED)."""
        return 100.0 * self.healthy / self.checks if self.checks else 0.0

    @property
    def avg_latency_ms(self):
        """Mean response time of successful requests, or None."""
        return sum(self.latencies) / len(self.latencies) if self.latencies else None

    @property
    def p95_latency_ms(self):
        """95th percentile response time of successful requests, or None."""
        if not self.latencies:
            return None
        ordered = sorted(self.latencies)
        return ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]


def summarise(rows):
    """Group history rows by URL and return TargetSummary objects in first-seen order."""
    summaries = {}
    for row in rows:
        s = summaries.setdefault(row["url"], TargetSummary(name=row["name"], url=row["url"]))
        s.checks += 1
        if row["status"] in HEALTHY:
            s.healthy += 1
            if row["status"] == "DEGRADED":
                s.degraded += 1
        else:
            s.failure_categories[row["category"] or "UNKNOWN"] += 1
            if s._last_status in HEALTHY or not s._last_status:
                s.incidents += 1
        if row["response_time_ms"]:
            s.latencies.append(float(row["response_time_ms"]))
        s._last_status = row["status"]
    return list(summaries.values())


def _fmt_ms(value):
    """Format a latency for display."""
    return "-" if value is None else f"{value:.0f}"


def _top_failure(s):
    """Return the most common failure category, or '-'."""
    return s.failure_categories.most_common(1)[0][0] if s.failure_categories else "-"


def render_text(summaries, hours):
    """Return the report as a fixed-width text table."""
    header = (
        f"{'Service':<24} {'Uptime':>8} {'Checks':>7} {'Degraded':>8} {'Incidents':>9} "
        f"{'Avg ms':>7} {'p95 ms':>7}  Top failure"
    )
    lines = [f"Uptime report - last {hours}h", "", header, "-" * len(header)]
    for s in summaries:
        lines.append(
            f"{s.name[:24]:<24} {s.uptime_pct:>7.2f}% {s.checks:>7} {s.degraded:>8} {s.incidents:>9} "
            f"{_fmt_ms(s.avg_latency_ms):>7} {_fmt_ms(s.p95_latency_ms):>7}  {_top_failure(s)}"
        )
    if not summaries:
        lines.append("no checks recorded in this period")
    return "\n".join(lines)


def render_html(summaries, hours, generated_at):
    """Return the report as a self-contained HTML page."""
    rows = []
    for s in summaries:
        css = "ok" if s.uptime_pct >= 99.9 else "warn" if s.uptime_pct >= 99 else "bad"
        rows.append(
            "<tr>"
            f"<td>{html.escape(s.name)}<br><small>{html.escape(s.url)}</small></td>"
            f'<td class="{css}">{s.uptime_pct:.2f}%</td>'
            f"<td>{s.checks}</td><td>{s.degraded}</td><td>{s.incidents}</td>"
            f"<td>{_fmt_ms(s.avg_latency_ms)}</td><td>{_fmt_ms(s.p95_latency_ms)}</td>"
            f"<td>{html.escape(_top_failure(s))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or '<tr><td colspan="8">No checks recorded in this period.</td></tr>'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Uptime report</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2328; }}
  table {{ border-collapse: collapse; width: 100%; max-width: 960px; }}
  th, td {{ text-align: left; padding: .5rem .75rem; border-bottom: 1px solid #d0d7de; }}
  th {{ background: #f6f8fa; }}
  small {{ color: #59636e; }}
  .ok {{ color: #1a7f37; font-weight: 600; }}
  .warn {{ color: #9a6700; font-weight: 600; }}
  .bad {{ color: #cf222e; font-weight: 600; }}
</style>
</head>
<body>
<h1>Uptime report</h1>
<p>Last {hours} hour{"" if hours == 1 else "s"} &middot; generated {generated_at:%Y-%m-%d %H:%M} UTC</p>
<table>
<tr><th>Service</th><th>Uptime</th><th>Checks</th><th>Degraded</th><th>Incidents</th>
<th>Avg ms</th><th>p95 ms</th><th>Top failure</th></tr>
{body}
</table>
</body>
</html>
"""


def main(argv=None):
    """Build the report from the history file. Returns a process exit code."""
    parser = argparse.ArgumentParser(description="Summarise service-watchdog check history.")
    parser.add_argument("--history", default="logs/history.csv", help="path to the history CSV")
    parser.add_argument("--hours", type=int, default=24, help="report window in hours")
    parser.add_argument("--html", metavar="PATH", help="also write an HTML report to PATH")
    args = parser.parse_args(argv)

    now = datetime.now(timezone.utc)
    summaries = summarise(history.read(args.history, since=now - timedelta(hours=args.hours)))
    print(render_text(summaries, args.hours))

    if args.html:
        os.makedirs(os.path.dirname(args.html) or ".", exist_ok=True)
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_html(summaries, args.hours, now))
        print(f"\nHTML report written to {args.html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
