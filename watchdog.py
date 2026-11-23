"""service-watchdog entry point: run checks on a schedule and send alerts."""

from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv

from alerter import build_message, send_email
from config import ConfigError, load_config
from logger import setup_logger
from monitor import DEGRADED, DOWN, check_target
from state import StateTracker


def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Monitor URLs and alert when they go down.")
    parser.add_argument("--config", default="config.yaml", help="path to the YAML config file")
    parser.add_argument(
        "--once",
        action="store_true",
        help="run one round of checks and exit (exit code 1 if anything is down)",
    )
    parser.add_argument("--dry-run", action="store_true", help="log alerts instead of sending email")
    return parser.parse_args(argv)


def email_credentials():
    """Return (sender, password, recipient) from the environment, or None if any is missing."""
    creds = tuple(os.getenv(k) for k in ("SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL"))
    return creds if all(creds) else None


def dispatch(event, settings, creds, logger, dry_run):
    """Send (or log, in dry-run mode) the alert for an Event."""
    subject, body = build_message(event)
    if dry_run or creds is None:
        logger.info("alert (not emailed): %s", subject)
        return
    sender, password, recipient = creds
    try:
        send_email(settings.smtp_server, settings.smtp_port, sender, password, recipient, subject, body)
        logger.info("alert emailed: %s", subject)
    except Exception as e:
        logger.error("failed to send alert '%s': %s", subject, e)


def run_round(settings, tracker, creds, logger, dry_run):
    """Check every target once; return the list of CheckResults."""
    results = []
    for target in settings.targets:
        result = check_target(target, settings.timeout, settings.tls_expiry_warning_days)
        level = {DOWN: logger.error, DEGRADED: logger.warning}.get(result.status, logger.info)
        level(result.log_line())

        event = tracker.update(result)
        if event:
            dispatch(event, settings, creds, logger, dry_run)
        results.append(result)
    return results


def main(argv=None):
    """Load config, then run checks once or forever. Returns a process exit code."""
    args = parse_args(argv)
    load_dotenv()
    logger = setup_logger()

    try:
        settings = load_config(args.config)
    except ConfigError as e:
        logger.error("configuration error: %s", e)
        return 2

    creds = email_credentials()
    if creds is None and not args.dry_run:
        logger.warning("email credentials not set in .env; alerts will only be logged")

    tracker = StateTracker(1 if args.once else settings.failure_threshold)
    logger.info(
        "watchdog started: %d targets, every %s min, alert after %d failures",
        len(settings.targets),
        settings.check_interval,
        tracker.failure_threshold,
    )

    try:
        while True:
            results = run_round(settings, tracker, creds, logger, args.dry_run)
            if args.once:
                return 1 if any(r.status == DOWN for r in results) else 0
            time.sleep(settings.check_interval * 60)
    except KeyboardInterrupt:
        logger.info("watchdog stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
