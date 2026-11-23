# Service Watchdog

A lightweight Python service that monitors a list of URLs and alerts you by email when any go down. It tracks downtime duration and sends a recovery notice when services come back up.

[![CI](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml/badge.svg)](https://github.com/Joun-Mikhail/service-watchdog/actions/workflows/ci.yml)

## Requirements

- Python 3.9+
- An email account with SMTP access (e.g., Gmail with an [App Password](https://support.google.com/accounts/answer/185833))

## Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/service-watchdog.git
   cd service-watchdog
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure email credentials:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your email credentials:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-app-password
   RECIPIENT_EMAIL=alert-recipient@example.com
   ```

4. **Run the watchdog:**
   ```bash
   python watchdog.py
   ```

## Adding URLs to Monitor

Edit `config.yaml` and add URLs to the `urls` list:

```yaml
urls:
  - https://www.google.com
  - https://www.github.com
  - https://your-service.example.com
```

You can also adjust the check interval and timeout:

```yaml
check_interval: 5   # minutes between checks
timeout: 10          # seconds per request
```

## Sample Log Output

```
2025-01-15 10:30:00 - INFO - Service Watchdog started. Monitoring 3 URLs every 5 minutes.
2025-01-15 10:30:01 - INFO - URL: https://www.google.com | Status: 200 | Response Time: 120.45 ms
2025-01-15 10:30:02 - INFO - URL: https://www.github.com | Status: 200 | Response Time: 250.30 ms
2025-01-15 10:30:03 - WARNING - URL: https://www.example.com | Status: 0 | DOWN | Error: ConnectionError
2025-01-15 10:30:03 - INFO - Down alert email sent for https://www.example.com
2025-01-15 10:35:04 - INFO - URL: https://www.example.com | Status: 200 | Response Time: 95.12 ms
2025-01-15 10:35:04 - INFO - URL: https://www.example.com | RECOVERED after 301 seconds
2025-01-15 10:35:04 - INFO - Recovery email sent for https://www.example.com
```

## Sample Alert Email

**Down alert:**
```
Subject: [ALERT] Service Down: https://www.example.com

Service Watchdog Alert

URL: https://www.example.com
Status: DOWN
Status Code: 0
Time: 2025-01-15 10:30:03
Error: ConnectionError

This is an automated alert from Service Watchdog.
```

**Recovery alert:**
```
Subject: [RECOVERY] Service Back Up: https://www.example.com

Service Watchdog Recovery Notice

URL: https://www.example.com
Status: UP (Recovered)
Time: 2025-01-15 10:35:04
Downtime Duration: 5m 1s

This is an automated alert from Service Watchdog.
```
