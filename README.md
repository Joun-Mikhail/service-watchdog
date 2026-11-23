# service-watchdog

[![CI](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml/badge.svg)](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

A lightweight Python uptime monitor that tells you **why** a service is down, not just that it is.
Each check walks the network stack layer by layer — DNS, TCP, TLS, HTTP — so the alert names the
layer that failed and points to the runbook for fixing it.

---

## Features

- **Layered diagnostics** — every failure is classified as `DNS`, `TCP`, `TLS`, `HTTP`, `CONTENT` or `LATENCY`
- **TLS certificate monitoring** — warns before certificates expire
- **Content and latency checks** — catch maintenance pages and slow responses, not just hard outages
- **Noise control** — alerts only after N consecutive failures, once per incident
- **Recovery notices** — reports total downtime when a service comes back
- **Structured logs** — `key=value` lines that are easy to grep or query, with automatic rotation
- **Scriptable** — `--once` exits non-zero when something is down, for cron jobs and CI
- **Uptime reports** — daily uptime %, incident count and p95 latency per service (text or HTML)
- **Runs anywhere** — Docker, a hardened systemd service on Linux, or Task Scheduler on Windows

---

## How it works

```
watchdog.py ──► monitor.py ──► diagnostics.py   DNS lookup → TCP connect → TLS handshake
                    │                            then HTTP request: status, keyword, latency
                    ▼
                state.py      consecutive-failure tracking, DOWN / DEGRADED / RECOVERED events
                    │
                    ▼
                alerter.py    email with diagnosis, details and runbook link (smtplib)
```

| Category       | Meaning                                   | Typical cause                              |
|----------------|-------------------------------------------|--------------------------------------------|
| `DNS`          | Hostname does not resolve                 | Expired domain, bad record, resolver issue |
| `TCP`          | Port refused, filtered or unreachable     | Service stopped, firewall, security group  |
| `TLS`          | Handshake or certificate validation fails | Expired / self-signed / mismatched cert    |
| `HTTP`         | Wrong status code or no response          | App error (5xx), bad deploy, overload      |
| `CONTENT`      | Expected keyword missing from the page    | Maintenance page, partial outage           |
| `LATENCY`      | Response slower than the configured limit | Resource exhaustion, slow dependency       |
| `TLS_EXPIRING` | Certificate expires soon                  | Renewal not automated or failing           |

---

## Quick start

```bash
git clone https://github.com/Joun-Mikhail/service-watchdog.git
cd service-watchdog
pip install -r requirements.txt
cp .env.example .env        # add SMTP credentials
python watchdog.py --once --dry-run
python watchdog.py
```

### Command-line options

| Flag          | Description                                                       |
|---------------|-------------------------------------------------------------------|
| `--config`    | Path to the config file (default `config.yaml`)                   |
| `--once`      | Run one round and exit — exit code `1` if any target is down      |
| `--dry-run`   | Log alerts instead of emailing them                               |

Exit codes: `0` all healthy, `1` at least one target down, `2` configuration error.

---

## Deployment

All three methods are installed and verified automatically in CI on every push.

### Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

The container runs as an unprivileged user; `config.yaml` is mounted read-only and logs persist in `./logs`.

### Linux (systemd)

```bash
sudo ./deploy/linux/install.sh
journalctl -u service-watchdog -f
```

Installs to `/opt/service-watchdog` with its own virtual environment and a dedicated `watchdog` system
user. The unit is sandboxed (`ProtectSystem=strict`, `NoNewPrivileges`, write access to `logs/` only),
restarts on failure, and does not restart-loop on a bad config (exit code 2). A systemd timer writes the
daily report to `/opt/service-watchdog/reports/uptime-latest.html` at 07:00.

### Windows (Task Scheduler)

From an elevated PowerShell in the repository folder:

```powershell
.\deploy\windows\Install-WatchdogTask.ps1
Get-Content .\logs\watchdog.log -Tail 20 -Wait
```

Registers a task that starts at boot and restarts on failure, plus a daily report task. Runs without
a stored password (S4U logon). Remove with `-Uninstall`.

---

## Uptime report

Every check is appended to `logs/history.csv`. Summarise it with:

```bash
python report.py                                  # last 24 hours
python report.py --hours 168 --html reports/weekly.html
```

```
Uptime report - last 24h

Service                    Uptime  Checks Incidents  Avg ms  p95 ms  Top failure
--------------------------------------------------------------------------------
Public API                 99.65%     288         1     121     188  HTTP
Shop                       98.96%     288         2     204     311  TCP
Blog                      100.00%     288         0     242     260  -
```

---

## Configuration

`config.yaml`:

```yaml
check_interval: 5            # minutes between rounds
timeout: 10                  # seconds per network operation
failure_threshold: 2         # consecutive failures before alerting
tls_expiry_warning_days: 14

targets:
  - name: Public API
    url: https://api.example.com/health
    expected_status: 200
    keyword: "ok"
    max_latency_ms: 1500

  - https://www.example.com   # plain URL: status 200 check only

email:
  smtp_server: smtp.gmail.com
  smtp_port: 587
```

`.env` (never committed):

```
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=alerts@your-team.com
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833), not your account password.

---

## Sample log

```
2026-11-23 10:30:00 | INFO    | watchdog started: 3 targets, every 5 min, alert after 2 failures
2026-11-23 10:30:01 | INFO    | status=UP name=Public API url=https://api.example.com/health code=200 latency_ms=118.4 ip=203.0.113.10 tls_days=64
2026-11-23 10:30:01 | ERROR   | status=DOWN name=Shop url=https://shop.example.com category=TCP ip=203.0.113.25 detail="connection to 203.0.113.25:443 refused"
2026-11-23 10:30:02 | WARNING | status=DEGRADED name=Blog url=https://blog.example.com category=TLS_EXPIRING code=200 latency_ms=240.7 tls_days=6 detail="certificate expires in 6 days"
2026-11-23 10:35:01 | ERROR   | status=DOWN name=Shop url=https://shop.example.com category=TCP ip=203.0.113.25 detail="connection to 203.0.113.25:443 refused"
2026-11-23 10:35:02 | INFO    | alert emailed: [DOWN] Shop - TCP failure
2026-11-23 10:45:01 | INFO    | status=UP name=Shop url=https://shop.example.com code=200 latency_ms=201.3 ip=203.0.113.25 tls_days=80
2026-11-23 10:45:02 | INFO    | alert emailed: [RECOVERED] Shop - back up after 15m 0s
```

## Sample alert

```
Subject: [DOWN] Shop - TCP failure

Service is DOWN

Service:     Shop
URL:         https://shop.example.com
Time:        2026-11-23 10:35:01
Failure:     TCP
Detail:      connection to 203.0.113.25:443 refused
Resolved IP: 203.0.113.25

Runbook:     docs/runbooks/connection-failure.md

-- service-watchdog
```

---

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest          # unit tests (network calls are mocked)
ruff check .    # lint
```

CI runs on every push and pull request: lint, tests on Python 3.10 – 3.13, a Docker build, and real
installs of the systemd service (Ubuntu) and the scheduled tasks (Windows).

---

## Project structure

```
watchdog.py        entry point, CLI and scheduling loop
config.py          config loading and validation
monitor.py         runs a check and classifies the result
diagnostics.py     DNS, TCP and TLS checks
state.py           failure threshold and incident tracking
alerter.py         alert message formatting and SMTP delivery
logger.py          rotating file + console logging
history.py         CSV check history
report.py          uptime report (text / HTML)
deploy/linux/      systemd units and installer
deploy/windows/    Task Scheduler installer
Dockerfile         container image (non-root)
tests/             pytest suite
```

## Known limitations

- DNS, TCP and TLS checks connect directly, so on networks that only allow outbound traffic through
  an HTTP proxy they report failures even when the site is reachable through the proxy.

---

## License

MIT
