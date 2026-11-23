# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-23

### Added

- Layered diagnostics for every check: DNS resolution, TCP connect, TLS handshake and certificate
  validation, HTTP status, response keyword and latency
- `DOWN`, `DEGRADED` and `RECOVERED` alerts with a consecutive-failure threshold, one alert per
  incident and total downtime on recovery
- Alert delivery by email (SMTP with STARTTLS) and AWS SNS
- Runbook link in every alert, with runbooks for each failure category
- Structured `key=value` logging with rotation
- Check history in CSV and `report.py` uptime report (text and HTML)
- Command-line options `--config`, `--once` and `--dry-run`, with meaningful exit codes
- Deployment as a Docker container, a hardened systemd service with a report timer, and Windows
  scheduled tasks
- Terraform for AWS: EC2 without SSH or inbound ports, least-privilege IAM, CloudWatch Logs, metric
  filters, alarms and dashboard, SNS alerts and automatic instance recovery
- Demo lab with local services for every failure type
- Troubleshooting toolkit, postmortem template and worked example
- CI: lint, tests with coverage on Python 3.10–3.15, Docker build, real Linux and Windows installs,
  Terraform validation, CodeQL and Dependabot
