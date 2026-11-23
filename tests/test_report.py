from datetime import datetime, timedelta, timezone

import history
import report
from monitor import DOWN, UP, CheckResult

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def record(path, minutes, status, category=None, latency=None):
    result = CheckResult(
        name="API", url="https://api.example.com", status=status, category=category, response_time_ms=latency
    )
    history.append(result, str(path), now=T0 + timedelta(minutes=minutes))


def test_history_round_trip_and_since_filter(tmp_path):
    path = tmp_path / "logs" / "history.csv"
    record(path, 0, UP, latency=100)
    record(path, 10, DOWN, category="TCP")

    rows = list(history.read(str(path)))
    assert [r["status"] for r in rows] == ["UP", "DOWN"]
    assert rows[1]["category"] == "TCP"

    recent = list(history.read(str(path), since=T0 + timedelta(minutes=5)))
    assert [r["status"] for r in recent] == ["DOWN"]


def test_missing_history_file_yields_nothing(tmp_path):
    assert list(history.read(str(tmp_path / "none.csv"))) == []


def test_summary_counts_uptime_incidents_and_latency(tmp_path):
    path = tmp_path / "history.csv"
    statuses = [UP, UP, DOWN, DOWN, UP, UP, DOWN, UP, UP, UP]
    for i, status in enumerate(statuses):
        record(
            path,
            i,
            status,
            category="HTTP" if status == DOWN else None,
            latency=100 + i if status == UP else None,
        )

    [s] = report.summarise(history.read(str(path)))

    assert s.checks == 10
    assert s.uptime_pct == 70.0
    assert s.incidents == 2
    assert s.failure_categories["HTTP"] == 3
    assert s.degraded == 0
    assert s.avg_latency_ms == sum(100 + i for i, st in enumerate(statuses) if st == UP) / 7
    assert s.p95_latency_ms == 109


def test_renderers_include_targets(tmp_path):
    path = tmp_path / "history.csv"
    record(path, 0, UP, latency=120)
    summaries = report.summarise(history.read(str(path)))

    text = report.render_text(summaries, 24)
    page = report.render_html(summaries, 24, T0)

    assert "API" in text and "100.00%" in text
    assert '<td class="ok">100.00%</td>' in page


def test_main_writes_html(tmp_path, capsys):
    path = tmp_path / "history.csv"
    history.append(CheckResult(name="API", url="https://x", status=UP), str(path))
    out = tmp_path / "reports" / "uptime.html"

    assert report.main(["--history", str(path), "--html", str(out)]) == 0
    assert out.exists()
    assert "Uptime report" in capsys.readouterr().out


def test_degraded_counts_as_up_but_is_reported(tmp_path):
    path = tmp_path / "history.csv"
    record(path, 0, UP, latency=100)
    record(path, 1, "DEGRADED", category="LATENCY", latency=2500)
    [s] = report.summarise(history.read(str(path)))

    assert s.uptime_pct == 100.0
    assert s.degraded == 1
    assert s.incidents == 0
