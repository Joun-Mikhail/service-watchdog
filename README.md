# service-watchdog

[![CI](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml/badge.svg)](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

A lightweight Python uptime monitor. Checks a list of URLs on a schedule, logs every result, and sends a single email alert when a service goes down. Sends a recovery notice with total downtime when it comes back up.

---

## How it works

```
watchdog.py  →  monitor.py   checks each URL, records status + response time
             →  alerter.py   sends DOWN alert (once) or RECOVERY with downtime
             →  logger.py    writes timestamped entries to logs/watchdog.log
             →  config.yaml  URLs, interval, timeout, SMTP settings
```

---

## Quick start

```bash
git clone https://github.com/Joun-Mikhail/service-watchdog.git
cd service-watchdog
pip install -r requirements.txt
cp .env.example .env
python watchdog.py
```

---

## Configuration

`config.yaml`:

```yaml
urls:
  - https://your-api.example.com/health
  - https://your-site.example.com
check_interval: 5
timeout: 10
```

`.env`:

```
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password
RECIPIENT_EMAIL=alerts@your-team.com
```

---

## Sample log

```
2026-11-23 10:30:01 - INFO    - https://your-api.example.com/health | 200 | 120ms
2026-11-23 10:30:03 - WARNING - https://your-site.example.com | DOWN | ConnectionError
2026-11-23 10:30:03 - INFO    - Down alert sent
2026-11-23 10:35:04 - INFO    - https://your-site.example.com | RECOVERED after 301s
2026-11-23 10:35:04 - INFO    - Recovery alert sent
```

---

## Project structure

```
watchdog.py        main loop
monitor.py         check_url() — status code, response time, up/down
alerter.py         send_down_alert() / send_recovery_alert() via smtplib
logger.py          file + console logging
config.yaml        URLs and settings
.env.example       credential template — copy to .env, never commit
requirements.txt   requests · pyyaml · python-dotenv
```

---

## License

MIT
