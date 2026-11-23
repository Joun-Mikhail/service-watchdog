"""service-watchdog entry point: run checks on a schedule and send alerts."""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

import history
from alerter import build_message, publish_sns, send_email
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


def _is_placeholder(value):
    """True for the template values shipped in .env.example."""
    return value.startswith("your-") or value.endswith("@example.com")


def email_credentials():
    """Return (sender, password, recipient) from the environment, or None if unset or still the template."""
    creds = tuple(os.getenv(k, "").strip() for k in ("SENDER_EMAIL", "SENDER_PASSWORD", "RECIPIENT_EMAIL"))
    if not all(creds) or any(_is_placeholder(v) for v in creds):
        return None
    return creds


@dataclass
class Notifier:
    """Delivers alerts to every configured channel: email (SMTP) and/or AWS SNS."""

    settings: object
    logger: object
    email_creds: Optional[tuple] = None
    sns_topic_arn: Optional[str] = None
    dry_run: bool = False

    @classmethod
    def from_env(cls, settings, logger, dry_run=False):
        """Build a Notifier from environment variables (.env is loaded beforehand)."""
        return cls(settings, logger, email_credentials(), os.getenv("ALERT_SNS_TOPIC_ARN") or None, dry_run)

    @property
    def channels(self):
        """Names of the channels alerts will be delivered to."""
        names = []
        if self.email_creds:
            names.append("email")
        if self.sns_topic_arn:
            names.append("sns")
        return names

    def send(self, event):
        """Deliver an Event; failures on one channel do not block the others."""
        subject, body = build_message(event)
        if self.dry_run or not self.channels:
            self.logger.info("alert (not sent): %s", subject)
            return
        if self.email_creds:
            sender, password, recipient = self.email_creds
            self._deliver(
                "email",
                subject,
                send_email,
                self.settings.smtp_server,
                self.settings.smtp_port,
                sender,
                password,
                recipient,
                subject,
                body,
            )
        if self.sns_topic_arn:
            self._deliver("sns", subject, publish_sns, self.sns_topic_arn, subject, body)

    def _deliver(self, channel, subject, func, *args):
        """Call one channel's send function and log the outcome."""
        try:
            func(*args)
            self.logger.info("alert sent via %s: %s", channel, subject)
        except Exception as e:
            self.logger.error("failed to send alert via %s '%s': %s", channel, subject, e)


def run_round(settings, tracker, notifier, logger):
    """Check every target once; return the list of CheckResults."""
    results = []
    for target in settings.targets:
        result = check_target(target, settings.timeout, settings.tls_expiry_warning_days)
        level = {DOWN: logger.error, DEGRADED: logger.warning}.get(result.status, logger.info)
        level(result.log_line())

        history.append(result, settings.history_file)
        event = tracker.update(result)
        if event:
            notifier.send(event)
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

    notifier = Notifier.from_env(settings, logger, args.dry_run)
    if not notifier.channels and not args.dry_run:
        logger.warning("no alert channel configured in .env (SMTP or SNS); alerts will only be logged")

    tracker = StateTracker(1 if args.once else settings.failure_threshold)
    logger.info(
        "watchdog started: %d targets, every %s min, alert after %d failures, channels: %s",
        len(settings.targets),
        settings.check_interval,
        tracker.failure_threshold,
        ", ".join(notifier.channels) or "none",
    )

    try:
        while True:
            results = run_round(settings, tracker, notifier, logger)
            if args.once:
                return 1 if any(r.status == DOWN for r in results) else 0
            time.sleep(settings.check_interval * 60)
    except KeyboardInterrupt:
        logger.info("watchdog stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
